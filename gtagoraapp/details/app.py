import json
import logging
import re
import subprocess
from base64 import b64decode
from logging.handlers import RotatingFileHandler
from pathlib import Path, PurePath
from typing import List

from gtagora import Agora
from gtagora.models.dataset import DatasetType

from gtagoraapp.details.settings import Settings
from gtagoraapp.details.ws import AgoraWebsocket


class App:
    def __init__(self):
        self.settings = Settings()

        if not self.settings.is_complete():
            raise ValueError('The app is not configured yet. Please run: "agoraapp.py --setup" first')

        self.logger = self._create_logger(self.settings.log_level, self.settings.console_log_level)
        self.logger.info('Starting the Agora App...')

        self.agora = Agora.create(self.settings.server, token=self.settings.session_key)

        if not self.ping():
            raise ConnectionError('Cannot connect to Agora: The server could not be reached')

        if not self.check_connection():
            raise ConnectionError('Cannot connect to Agora: Please check your credentials')

        self.logger.info(f'Successfully connected to Agora at {self.settings.server}')

        self.websocket = AgoraWebsocket(self.settings, self)

    def run(self):
        self.websocket.run()

    def ping(self):
        return self.agora.ping()

    def check_connection(self):
        return self.agora.http_client.check_connection

    def download(self, files):
        try:
            self.logger.info(f'Downloading {len(files)} files:')
            count = 0
            for file in files:
                if len(file) == 5 or len(file) == 4:
                    id = file[0]
                    dir_name = file[1]
                    filename = file[2]
                    size = file[3]
                    if len(file) == 5:
                        hash = file[4]
                    else:
                        hash = None

                    download_path = PurePath(self.settings.download_path, dir_name)
                    Path(download_path).mkdir(parents=True, exist_ok=True)
                    download_file = PurePath(download_path, filename)
                    url = f'/api/v1/datafile/{id}/download/'
                    self.logger.info(f'    {self.agora.http_client.connection.url}/{url}  -->  {download_file.as_posix()}')
                    self.agora.http_client.download(url, download_file.as_posix())
                    count += 1
            self.logger.info(f'Successfully downloaded {count} files')
        except Exception as e:
            self.logger.error(f'Error downloading files: {str(e)}')

        self.logger.info(f'Download Complete')
        self.logger.info(f' ')

    def run_task(self, data):
        try:
            name = data.get('name')
            self.logger.info(' ')
            self.logger.info(f'Running task: "{name}"')

            task_info_id = data.get('taskInfo')
            output_directory = data.get('outputDirectory')
            commandline = data.get('commandLine')
            outputs = data.get('outputs')
            target = data.get('target')
            script = data.get('script')
            script_path = data.get('scriptPath')

            # download datafiles
            files = data.get('files')
            if files:
                self.download(files)

            # replace base path
            (output_directory, replacements) = self._prepare_output_directory(output_directory)

            if script and script_path:
                if not self._save_script(script_path, script):
                    return

            stdout = None
            error = None
            if commandline:
                self.logger.debug(f'  Replacing placeholders in command line:')
                commandline = self._replace_base_path(commandline, replacements)

                (data, error, stdout) = self._perform_task(commandline)

            if outputs and output_directory and target:
                files = self._collect_outputs(outputs, output_directory)

                if files:
                    target_id = target[0]
                    target_type = target[1]

                    self._upload_files(target_id, target_type, files)
                else:
                    self.logger.debug(f'  No files found to upload')

            if task_info_id:
                self._mark_task_as_finished(task_info_id, data, error)
                if stdout:
                    self._upload_stdout(task_info_id, stdout)

        except Exception as e:
            self.logger.error(f'Error executing task: {str(e)}')

        self.logger.info(f'Task Complete')
        self.logger.info(f' ')

    def _perform_task(self, command):
        data = dict()
        error = None
        self.logger.info(f'  Executing command:')
        self.logger.info(f'    {command}')
        data['command'] = command
        try:
            stdout = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
            data['exit_code'] = 0
            self.logger.info(f'  Command successfully completed')
        except subprocess.CalledProcessError as e:
            error = f'{e.output}'
            data['exit_code'] = e.returncode
            self.logger.error(f'The process returned a non-zero exit code: exit code: {e.returncode}; message: {e.output}')
        return (data, error, stdout)

    def _prepare_output_directory(self, output_directory):
        output_directory_orig = output_directory
        output_directory = self._replace_base_path(output_directory, [('{{BASE_PATH}}', self.settings.download_path)])
        output_directory = Path(output_directory)
        self.logger.debug(f'  Replaced placeholders in output path:')
        self.logger.debug(f'    {output_directory_orig} -->  {output_directory_orig}')
        output_directory.mkdir(parents=True, exist_ok=True)
        output_directory_orig_data = (Path(output_directory_orig).parent / 'data').as_posix()
        output_directory_data = output_directory.parent / 'data'
        replacements = [(output_directory_orig, str(output_directory)),
                        (output_directory_orig_data, str(output_directory_data))]
        return (output_directory, replacements)

    def _replace_base_path(self, input_str: str, replacements: List[tuple]):
        output_str = input_str
        for replacement in replacements:
            output_str = output_str.replace(replacement[0], replacement[1])
            self.logger.debug(f'    {replacement[0]} -->  {replacement[1]}')
        return output_str

    def _save_script(self, script_path, script):
        script_path = script_path.replace('{{BASE_PATH}}', self.settings.download_path)
        self.logger.debug(f'  Saving the script to {script_path}')
        scriptDir = Path(script_path).parent
        scriptDir.mkdir(parents=True, exist_ok=True)
        decoded_script = b64decode(script)
        with open(script_path, 'wb') as file:
            file.write(decoded_script)
        if not Path(script_path).exists():
            self.logger.error(f'Cannot create the script to run')
            return False
        return True

    def _collect_outputs(self, outputs, output_directory):
        self.logger.info(f'  Collecting outputs:')
        files = []
        counter = 1
        for output in outputs:
            type = output.get('type')
            regex = output.get('regex')
            datasetType = output.get('datasetType')

            self.logger.info(f'    {counter}. type = {type}, regex = {regex}, datasetType = {datasetType}: ')

            if datasetType == DatasetType.PHILIPS_REC:
                cur_files = self._find_all_par_recs_in_directory(output_directory)
            elif datasetType == DatasetType.DICOM:
                cur_files = self._find_all_dicoms_in_directory(output_directory)
            elif datasetType == DatasetType.OTHER:
                cur_files = self._find_all_files_in_directory(output_directory)
            else:
                self.logger.error(f'The upload dataset type is not yet implemented. Please contact GyroTools')

            for file in cur_files:
                self.logger.info(f'      {file}')

            if not cur_files:
                self.logger.info(f'      No files found')

            files.extend(cur_files)
            counter += 1
        return files

    def _upload_files(self, target_id, target_type, files):
        try:
            self.logger.info(f'  Uploading output files to {target_type} {target_id}:')
            if target_type == 'folder':
                folder = self.agora.get_folder(target_id)
                folder.upload(files)
            elif target_type == 'serie':
                series = self.agora.get_series(target_id)
                series.upload(files)
            else:
                self.logger.error(f'Upload target type is not implemented yet. Please contact GyroTools')
        except Exception as e:
            self.logger.error(f'Error uploading files: {str(e)}')
            return False

    def _find_all_par_recs_in_directory(self, dir: Path, regex=None):
        if regex:
            r = re.compile(regex)
        else:
            r = re.compile('.*')

        recs = [f for f in dir.rglob('*.rec') if f.is_file() and r.match(f.as_posix())]
        pars = [f for f in dir.rglob('*.par') if f.is_file() and r.match(f.as_posix())]

        files = recs
        files.extend(pars)
        return files

    def _find_all_dicoms_in_directory(self, dir: Path, regex=None):
        if regex:
            r = re.compile(regex)
        else:
            r = re.compile('.*')

        return [f for f in dir.rglob('*') if f.is_file() and self.is_dicom_file(f) and r.match(f.as_posix())]

    def _find_all_files_in_directory(self, dir: Path, regex=None):
        if regex:
            r = re.compile(regex)
        else:
            r = re.compile('.*')

        return [f for f in dir.rglob('*') if f.is_file() and r.match(f.as_posix())]

    def _mark_task_as_finished(self, timeline_id, data, error):
        url = f'/api/v2/timeline/{timeline_id}/finish/'
        self.logger.debug(f'  Mark task as finished with url: {url}')
        status = self.agora.http_client.post(url, data={'data': json.dumps(data), 'error': error})
        if status.status_code == 404:
            url = f'/api/v1/taskinfo/{timeline_id}/finish/'
            self.logger.debug(f'  Mark task as finished with url: {url}')
            status = self.agora.http_client.post(url, data={'data': json.dumps(data), 'error': error})
            if status.status_code != 200:
                self.logger.warning(f'Could not mark the task as finish. status = {status.status_code}')

    def _upload_stdout(self, timeline_id, stdout):
        url = f'/api/v2/timeline/{timeline_id}/stdout/'
        self.logger.debug(f'  Send stdout to url: {url}')
        status = self.agora.http_client.post(url, data=stdout)
        if status.status_code == 404:
            url = f'/api/v1/taskinfo/{timeline_id}/stdout/'
            self.logger.debug(f'  Send stdout to url: {url}')
            status = self.agora.http_client.post(url, data=stdout)
            if status.status_code != 200:
                self.logger.warning(f'Could not upload the stdout. status = {status.status_code}')

    def _create_logger(self, level='INFO', console_level='INFO'):
        rotating_logger = logging.getLogger('gtagora-app-py')
        rotating_logger.setLevel(level)

        handler = RotatingFileHandler(
            self.settings.logfile, maxBytes=1024*1024*10, backupCount=10)
        formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s:  %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        rotating_logger.addHandler(handler)

        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(fmt='%(levelname)s:  %(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(console_level)
        rotating_logger.addHandler(console_handler)
        return rotating_logger

    @staticmethod
    def is_dicom_file(file: Path):
        try:
            with file.open("rb") as f:
                f.seek(128)
                magic = f.read(4)
                return magic == b'DICM'
        except:
            logging.getLogger('gtagora-app-py').debug(f'Dicom check failed on file {str(file)}')
            return False

    @staticmethod
    def get_session_key(server:str, username: str, password: str):
        logging.getLogger('gtagora-app-py').info(f'Getting session key for user {username}')
        A = Agora.create(server, user=username, password=password)
        if not A.ping():
            raise ConnectionError('Cannot connect to Agora: The server could not be reached')

        if not A.http_client.check_connection():
            raise ConnectionError('Cannot connect to Agora: Please check your credentials')

        return A.http_client.connection.token



