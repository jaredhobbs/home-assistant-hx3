import copy
import logging
import time

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

logger = logging.getLogger(__name__)


class ConnectionStatus:
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    INITIALIZING = "INITIALIZING"


class Setpoint:
    HEAT = "HEAT"
    COOL = "COOL"


class ActiveDemand:
    OFF = "OFF"
    HEAT = "HEAT"
    COOL = "COOL"


class ScheduleOverride:
    CANCELLED = "CANCELLED"
    NEXT_EVENT = "NEXT_EVENT"
    HOURS_01 = "HOURS_01"
    HOURS_02 = "HOURS_02"
    HOURS_03 = "HOURS_03"
    HOURS_04 = "HOURS_04"
    HOURS_05 = "HOURS_05"
    HOURS_06 = "HOURS_06"
    HOURS_07 = "HOURS_07"
    HOURS_08 = "HOURS_08"
    HOURS_09 = "HOURS_09"
    HOURS_10 = "HOURS_10"
    HOURS_11 = "HOURS_11"
    HOURS_12 = "HOURS_12"


class Mode:
    OFF = "OFF"
    AUTO = "AUTO"
    HEAT = "HEAT"
    COOL = "COOL"
    EHEAT = "EHEAT"
    MAXHEAT = "MAXHEAT"
    MAXCOOL = "MAXCOOL"


class FanMode:
    AUTO = "AUTO"
    FIFTEEN = "FIFTEEN"
    THIRTY = "THIRTY"
    FORTYFIVE = "FORTYFIVE"
    ALWAYS = "ALWAYS"


class AccountStatus:
    CONFIRMED = "CONFIRMED"
    UNCONFIRMED = "UNCONFIRMED"


class HxError(Exception):
    pass


class ConnectionTimeout(HxError):
    pass


class ConnectionError(HxError):
    pass


class SessionTimedOut(HxError):
    pass


class AuthError(HxError):
    pass


class APIError(HxError):
    pass


class APIRateLimited(APIError):
    def __init__(self):
        super().__init__("You are being rate-limited. Try waiting a bit.")


class Controller:
    def __init__(self, client, location):
        self._client = client
        self._location = location
        self._data = {}
        self._last_refresh = 0
        self._alive = None
        self._commslost = None
        self._id = None
        self._name = None

    @classmethod
    def from_location_response(cls, client, location, response):
        self = cls(client, location)
        self._id = response["id"]
        self._name = response["name"]
        self.refresh()
        return self

    def refresh(self):
        data = self._client._get_thermostat_data(self.id)
        if not data:
            raise APIError(f"API reported failure to query device {self.id}")
        self._alive = not data["disabled"]
        self._commslost = (
            data["location"]["connectionStatus"] == ConnectionStatus.OFFLINE
        )
        self._data = data
        self._last_refresh = time.time()

    @property
    def id(self):
        """The controller identifier"""
        return self._id

    @property
    def name(self):
        """The user-set name of this device"""
        return self._name

    @property
    def is_alive(self):
        """A boolean indicating whether the device is connected"""
        return self._alive and not self._commslost

    @property
    def away(self):
        """A boolean indicating whether the device is in away mode"""
        return self._data["away"]["active"]

    @away.setter
    def away(self, active):
        if not isinstance(active, bool):
            raise HxError(f"Invalid away mode `{active}`")
        if self.away is active:
            return
        self._client._set_thermostat_data(
            {
                "func": "changeAway",
                "input_type": "ChangeAwayInput!",
                "input_vals": {
                    "id": self.id,
                    "active": active,
                },
                "errors": ["NotFound"],
            },
        )
        self._data["away"]["active"] = active

    @property
    def humidification(self):
        return self._data["humidification"]

    @property
    def fan_running(self):
        """Returns a boolean indicating the current state of the fan"""
        return self._data["fan"]["active"]

    @property
    def fan_mode(self):
        """Returns one of FAN_MODES indicating the current setting"""
        return self._data["fan"]["mode"]

    @fan_mode.setter
    def fan_mode(self, mode):
        if mode not in self._data["fan"]["modes"]:
            raise HxError(f"Invalid fan mode `{mode}`")
        if self.fan_mode == mode:
            return
        self._client._set_thermostat_data(
            {
                "func": "changeFanMode",
                "input_type": "ChangeFanModeInput!",
                "input_vals": {
                    "id": self.id,
                    "mode": mode,
                },
                "errors": ["NotFound", "NotSupported"],
            },
        )
        self._data["fan"]["mode"] = mode

    @property
    def fan_modes(self):
        return self._data["fan"]["modes"]

    @property
    def system_mode(self):
        return self._data["mode"]

    @system_mode.setter
    def system_mode(self, mode):
        if mode not in self._data["modes"]:
            raise HxError(f"Invalid system mode `{mode}`")
        if self.system_mode == mode:
            return
        self._client._set_thermostat_data(
            {
                "func": "changeMode",
                "input_type": "ChangeModeInput!",
                "input_vals": {
                    "id": self.id,
                    "mode": mode,
                },
                "errors": ["NotFound"],
            },
        )
        self._data["mode"] = mode

    @property
    def system_modes(self):
        return self._data["modes"]

    @property
    def active_demand(self):
        return self._data["activeDemand"] or ActiveDemand.OFF

    @property
    def setpoint_cool(self):
        """The target temperature when in cooling mode"""
        return self._data["setpoints"]["cool"]

    @setpoint_cool.setter
    def setpoint_cool(self, temp):
        lower = self._data["coolRange"]["min"]
        upper = self._data["coolRange"]["max"]
        if temp > upper or temp < lower:
            raise HxError(f"Setpoint outside range {lower}-{upper}")
        self._client._set_thermostat_data(
            {
                "func": "changeSetpoint",
                "input_type": "ChangeSetpointInput!",
                "input_vals": {
                    "id": self.id,
                    "setpoint": Setpoint.COOL,
                    "value": temp,
                },
                "errors": ["NotFound", "AwayModeActive", "VacationModeActive"],
            },
        )
        self._data["setpoints"]["cool"] = temp

    @property
    def setpoint_heat(self):
        """The target temperature when in heating mode"""
        return self._data["setpoints"]["heat"]

    @setpoint_heat.setter
    def setpoint_heat(self, temp):
        lower = self._data["heatRange"]["min"]
        upper = self._data["heatRange"]["max"]
        if temp > upper or temp < lower:
            raise HxError(f"Setpoint outside range {lower}-{upper}")
        self._client._set_thermostat_data(
            {
                "func": "changeSetpoint",
                "input_type": "ChangeSetpointInput!",
                "input_vals": {
                    "id": self.id,
                    "setpoint": Setpoint.HEAT,
                    "value": temp,
                },
                "errors": ["NotFound", "AwayModeActive", "VacationModeActive"],
            },
        )
        self._data["setpoints"]["heat"] = temp

    @property
    def current_temperature(self):
        """The current measured ambient temperature"""
        return self._data["indoorTemp"]

    @property
    def current_humidity(self):
        """The current measured ambient humidity"""
        return self._data["humidity"]

    @property
    def outdoor_temperature(self):
        """The current measured outdoor temperature"""
        return self._data["outdoorTemp"]

    @property
    def temperature_unit(self):
        """The temperature unit currently in use. Either 'F' or 'C'"""
        return self._client._temperature_unit

    @property
    def raw_data(self):
        """The raw uiData structure from the API.

        Note that this is read only!
        """
        return copy.deepcopy(self._data)

    @property
    def brand(self):
        return self._location._brand

    @property
    def model(self):
        return self._location._model

    @property
    def location_name(self):
        return self._location._name

    @property
    def version(self):
        return self._location._version

    def __repr__(self):
        return "Controller<%s:%s>" % (self.id, self.name)


class Location:
    def __init__(self, client):
        self._client = client
        self._controllers = {}
        self._id = None
        self._name = None
        self._brand = None
        self._model = None
        self._version = None
        self._latitude = None
        self._longitude = None

    @classmethod
    def from_api_response(cls, client, api_response):
        self = cls(client)
        self._id = api_response["id"]
        self._name = api_response["name"]
        self._brand = api_response["brand"]
        self._model = api_response["model"]
        self._version = api_response["version"]["bootloader"]
        self._latitude = api_response["lat"]
        self._longitude = api_response["lng"]
        controllers = api_response["controllers"]
        self._controllers = [
            Controller.from_location_response(client, self, controller)
            for controller in controllers
        ]
        return self

    @property
    def controllers_by_id(self):
        """A dict of controllers indexed by id"""
        return {controller.id: controller for controller in self._controllers}

    @property
    def controllers_by_name(self):
        """A dict of controllers indexed by name.

        Note that if you have multiple controllers with the same name,
        this may not return them all!
        """
        return {controller.name: controller for controller in self._controllers}

    @property
    def id(self):
        """The location identifier"""
        return self._id

    def __repr__(self):
        return "Location<%s>" % self.id


class Hx3Api:
    _controller_data = """\
{
  id
  activeDemand
  activeScheduleEvent {
    day
    fanMode
    setpoints {
      heat
      cool
    }
    slot
    start {
      day
      hour
      minute
    }
    stop {
      day
      hour
      minute
    }
  }
  airflow
  airflowTestActive
  away {
    active
    setpoints {
      heat
      cool
    }
  }
  coolRange {
    min
    max
  }
  deadband
  dehumidification {
    max
    min
    mode
    value
  }
  disabled
  fan {
    active
    cfm
    mode
    modes
    override
  }
  heatRange {
    min
    max
  }
  humidification {
    max
    min
    mode
    value
  }
  humidity
  indoorTemp
  location {
    connectionStatus
  }
  mode
  modes
  name
  outdoorTemp
  schedule {
    day
    awake {
      day
      fanMode
      setpoints {
        heat
        cool
      }
      slot
      start {
        day
        hour
        minute
      }
      stop {
        day
        hour
        minute
      }
    }
    leave {
      day
      fanMode
      setpoints {
        heat
        cool
      }
      slot
      start {
        day
        hour
        minute
      }
      stop {
        day
        hour
        minute
      }
    }
    arrive {
      day
      fanMode
      setpoints {
        heat
        cool
      }
      slot
      start {
        day
        hour
        minute
      }
      stop {
        day
        hour
        minute
      }
    }
    bed {
      day
      fanMode
      setpoints {
        heat
        cool
      }
      slot
      start {
        day
        hour
        minute
      }
      stop {
        day
        hour
        minute
      }
    }
    events {
      day
      fanMode
      setpoints {
        heat
        cool
      }
      slot
      start {
        day
        hour
        minute
      }
      stop {
        day
        hour
        minute
      }
    }
  }
  scheduleOverride
  setpoints {
    heat
    cool
  }
  tempOverride
  zone
  zoneSensor {
    sensor
    version
  }
  zoning
  humidityNotification {
    enabled
    min
    max
  }
  temperatureNotification {
    enabled
    min
    max
  }
  accessLevel
}"""

    def __init__(self, email, token=None, access_token=None, refresh_token=None, ttl=None, last_refresh=0):
        self.__retries = 0
        self._email = email
        self._token = token
        self._transport = RequestsHTTPTransport(
            url="https://hx-thermostat.herokuapp.com",
            use_json=True,
            headers={"Content-type": "application/json"},
            verify=True,
            retries=3,
        )
        self._client = Client(
            transport=self._transport,
            fetch_schema_from_transport=False,
        )
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._ttl = ttl
        self._last_refresh = last_refresh
        self._temperature_unit = None
        self._locations = {}
        if self._access_token:
            self._ttl = None
            self._get_new_token()
            self._me()
        elif self._token:
            self._authenticate()
        else:
            raise AuthError('A valid token or access_token is required.')
        self._discover()

    def _execute(self, query: str, values: dict = None) -> dict:
        if self._access_token:
            if self._ttl:
                ttl = self._ttl - (time.time() - self._last_refresh)
                if ttl < 300:
                    self._ttl = None
                    self._get_new_token()
            self._transport.headers = {
                "Authorization": f"Bearer {self._access_token}",
            }
        query = gql(query)
        try:
            ret = self._client.execute(
                query,
                variable_values=values,
            )
            self.__retries = 0
            return ret
        except Exception as e:  # noqa
            if 'UNAUTHENTICATED' in f'{e}' and self.__retries < 5:
                self.__retries += 1
                self._authenticate()
                return self._execute(query, values=values)
            self.__retries = 0
            raise e

    def _authenticate(self) -> None:
        mutation = """\
mutation signIn($input: SignInInput!) {
  signIn(input: $input) {
    ... on SignInSuccess {
      accessToken
      refreshToken
      ttl
      user {
        temperatureUnit
      }
    }
    ... on TokenInvalid {
      message
    }
    ... on EmailInvalid {
      message
    }
  }
}"""
        result = self._execute(
            mutation,
            values={
                "input": {
                    "email": self._email,
                    "token": self._token,
                },
            },
        )
        data = result["signIn"]
        if "message" in result:
            msg = result["message"]
            logger.error(f"Failed to authenticate: {msg}")
            raise AuthError(msg)
        if "message" in data:
            msg = data["message"]
            logger.error(f"Failed to authenticate: {msg}")
            raise AuthError(msg)
        self._last_refresh = time.time()
        self._access_token = data["accessToken"]
        self._refresh_token = data["refreshToken"]
        self._ttl = data["ttl"]
        self._temperature_unit = data["user"]["temperatureUnit"]

    def _get_new_token(self) -> None:
        mutation = """\
mutation refreshToken($input: RefreshTokenInput!) {
  refreshToken(input: $input) {
    ... on RefreshTokenSuccess {
      accessToken
      refreshToken
      ttl
    }
    ... on TokenInvalid {
      message
    }
  }
}"""
        result = self._execute(
            mutation,
            values={
                "input": {
                    "token": self._refresh_token,
                },
            },
        )
        data = result["refreshToken"]
        if "message" in result:
            msg = result["message"]
            logger.error(f"Failed to get new token: {msg}")
            raise AuthError(msg)
        if "message" in data:
            msg = data["message"]
            logger.error(f"Failed to get new token: {msg}")
            raise AuthError(msg)
        self._last_refresh = time.time()
        self._access_token = data["accessToken"]
        self._refresh_token = data["refreshToken"]
        self._ttl = data["ttl"]

    def _get_locations(self) -> [dict]:
        query = f"""\
{{
  locations {{
    id
    brand
    lat
    lng
    model
    name
    controllers {self._controller_data}
    version {{
      application
      bootloader
      outdoorControl
    }}
  }}
}}"""
        result = self._execute(query)
        return result["locations"]

    def _me(self) -> None:
        query = """\
{
  me {
    temperatureUnit
  }
}"""
        result = self._execute(query)
        data = result["me"]
        self._temperature_unit = data['temperatureUnit']

    def _discover(self) -> None:
        for loc in self._get_locations():
            location = Location.from_api_response(self, loc)
            self._locations[location.id] = location

    @property
    def locations_by_id(self):
        """A dict of all locations indexed by id"""
        return self._locations

    @property
    def default_controller(self):
        """This is the first controller found.

        It is only useful if the account has only one controller and location
        in your account (which is pretty common). It is None if there
        are no devices in the account.
        """
        for location in self.locations_by_id.values():
            for device in location.devices_by_id.values():
                return device
        return None

    def get_controller(self, controller_id):
        """Find a controller by id."""
        for location in self.locations_by_id.values():
            for ident, controller in location.controller_by_id.items():
                if ident == controller_id:
                    return controller

    def _get_thermostat_data(self, controller_id) -> dict:
        query = f"""\
query controller($id: ID!) {{
  controller(id: $id) {self._controller_data}
}}"""
        result = self._execute(
            query,
            values={
                "id": controller_id,
            },
        )
        return result["controller"]

    def _set_thermostat_data(self, opts):
        func = opts["func"]
        input_type = opts["input_type"]
        input_values = opts["input_vals"]
        errors = "\n".join([f"... on {err} {{ message }}" for err in opts["errors"]])
        mutation = f"""\
mutation {func}($input: {input_type}) {{
  {func}(input: $input) {{
    {errors}
  }}
}}"""
        result = self._execute(
            mutation,
            values={"input": input_values},
        )
        data = result[func]
        if "message" in result:
            msg = result["message"]
            logger.error(f"Failed to run {func}: {msg}")
            raise HxError(msg)
        return data
