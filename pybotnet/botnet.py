""""""
from typing import Dict, List, Optional
from functools import wraps
import datetime
import logging
import uuid
import time

from .request import Request as Request
from .exceptions import UserException, EngineException

_logger = logging.getLogger(f"__{__name__}   ")


class BotNet:
    default_scripts = {}

    def __init__(
        self,
        engine=None,
        *,
        version: str = "0.1.0",
        delay: int = 2,
        debug: bool = False,
        use_default_scripts: bool = True,
        **extra,
    ):

        self._debug = debug
        self.version = version
        self.delay = delay
        self.engine = engine
        self.use_default_scripts = use_default_scripts
        self.scripts = {}

        if self.use_default_scripts:
            self.scripts.update(**BotNet.default_scripts)

        if self._debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        _logger.debug(
            f"init BotNet, default scripts: {list(BotNet.default_scripts.keys())}, engine: <{self.engine}>"
        )

    def __str__(self):
        return f"BotNet Version: {self.version}, scripts: {list(self.scripts.keys())}"

    @classmethod
    def deafult_script(
        cls, *, script_name=None, script_version: Optional[str] = None, **extra
    ):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):

                return func(*args, **kwargs)

            wrapper.__name__ = script_name or func.__name__
            wrapper.__doc__ = func.__doc__
            wrapper.__extra__ = {}
            wrapper.__extra__.update(
                {"script_version": script_version, "deafult_script": True}
            )

            cls.default_scripts.update({script_name or func.__name__: wrapper})
            return wrapper

        return decorator

    def add_script(
        self, *, script_name=None, script_version: Optional[str] = None, **extra
    ):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):

                return func(*args, **kwargs)

            wrapper.__name__ = script_name or func.__name__.strip().replace(" ", "_")
            wrapper.__doc__ = func.__doc__
            wrapper.__extra__ = {}
            wrapper.__extra__.update(
                {"script_version": script_version, "deafult_script": False}
            )

            self.scripts.update({script_name or func.__name__: wrapper})
            return wrapper

        return decorator

    def _help(self, script_name=None) -> str:
        all_scripts_name = list(self.scripts.keys())
        all_scripts_name.append("help")
        all_scripts_name = ", ".join(all_scripts_name)
        help = f"""
All scripts name: \n\t{all_scripts_name} 

Get more details about a script:
    `/help script-name`

Run script:
    `/command-name [params]`

    Example:
        `/echo 10 message`

        """
        if script_name:

            if script_name == 'help':
                return help

            script = self.scripts.get(script_name)
            if script:
                extra = ""
                for k, v in script.__extra__.items():
                    extra += f"\n{k}: {v}"

                return f"""NAME:\n{script.__name__}\n\nDESCRIPTION:\n"{script.__doc__}"\n{extra}"""

            else:
                return f"script `{script_name}` not found\n" + help

        return help

    def _create_request(self, command: List, meta_data: Dict) -> Request:
        request = Request()
        request.engine = self.engine
        request.command = command
        request.meta_data = meta_data
        request.sytsem_data = {"mac_addres": uuid.getnode()}
        request.time_stamp = datetime.datetime.now()
        return request

    def run(self):

        while True:
            try:
                command = self.engine.receive()

            except EngineException as e:
                _logger.debug(f"Engine[{self.engine}] Error: {e}")
                command = False

            except Exception as e:
                _logger.debug(f"Engine[{self.engine}] Error: {e}")
                command = False

            if not command or not command[0].startswith("/"):
                _logger.debug("<There is no command to execute>")
                time.sleep(self.delay)
                continue

            command[0] = command[0][1:]  # remove slash

            if command[0] == "help":
                _help_script_name = None
                
                if len(command) > 1:
                    _help_script_name = command[1]

                self.engine.send(self._help(_help_script_name))
                time.sleep(self.delay)
                continue
                
            script = self.scripts.get(command[0])

            if script:
                command = command[1:]

                meta_data = {
                    "script_name": script.__name__,
                    "script_version": script.__extra__.get("script_version"),
                    "script_doc": script.__doc__,
                }

                _logger.debug(
                    f"<BotNet.run: {meta_data['script_name']} {meta_data['script_version']}>"
                )

                request: Request = self._create_request(
                    command=command, meta_data=meta_data
                )

                try:
                    ret = script(request, *command)

                except UserException as e:
                    ret = e

                except Exception as e:
                    ret = f"internal error \n\n{e}"

                finally:
                    self.engine.send(ret)
                    time.sleep(self.delay)

            else:
                _logger.debug(f"<There is no script [{command[0]}] to execute>")
                time.sleep(self.delay)

    def import_scripts(self, external_scripts: "ExternalScripts"):
        _logger.debug(f"import_scripts: {list(external_scripts.scripts.keys())} ")
        self.scripts.update(**external_scripts.scripts)


class ExternalScripts(BotNet):
    def __init__(self):
        self.scripts = {}
