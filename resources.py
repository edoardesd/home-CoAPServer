import json
import datetime
import threading
import random
import logging
from urlparse import urlparse
from coapthon import defines
from coapthon.resources.resource import Resource
from coapthon.messages.response import Response

logger = logging.getLogger(__name__)

UPPER_TEMP = 32.9
LOWER_TEMP = 12.5

VALID_DOOR_QUERY = ["status", "color"]
VALID_DOOR_STATUS = ["CLOSED", "OPEN"]
VALID_POST = ["create"]


def read_temperature():
    return str(round(random.uniform(UPPER_TEMP, LOWER_TEMP), 2))


def check_json(val):
    if isinstance(val, (int, float, str)):
        return False
    else:
        return True


def dispatch_query(_key, _value):
    return {
        "status": _value if _value in VALID_DOOR_STATUS else "ERROR",
        "living_room": "Available resources: Temperature, Door and Light",
        "dining_room": "Available resources: Temperature, Door and Light"
    }.get(_key, "Invalid query")


def periodic_read(server, timeout):
    with server.lock:
        new_temp = read_temperature()
        if server.temperature == new_temp:
            return None

        server.temperature = new_temp
        server.now = datetime.datetime.now().strftime('%m%d%H%M%S')

        if check_json(server.value):
            server.value = [{"name": server.name, "value": server.temperature, "time": server.now}]
            try:
                server.payload = (50, json.dumps(server.value))
            except ValueError as e:
                print(e)

        if not check_json(server.value):
            server.value = server.temperature
            server.payload = (0, server.value)

        if not server._coap_server.stopped.isSet():
            timer = threading.Timer(random.uniform(timeout[0], timeout[1]), periodic_read, args=(server,timeout, ))
            timer.setDaemon(True)
            timer.start()

            if server._coap_server._observeLayer._relations and server._coap_server is not None:
                server._coap_server.notify(server)
                server.observe_count += 1


class BasicTemperatureResource(Resource):
    def __init__(self, name="Temp", coap_server=None):
        super(BasicTemperatureResource, self).__init__(name, coap_server, visible=True, observable=True,
                                                       allow_children=True)
        self.coap_server = coap_server
        self.lock = threading.Lock()
        self._content_type = "text/plain"
        self.temperature = 0
        self.now = 0
        self.value = self.temperature
        periodic_read(self, (3, 6))

    def render_GET(self, request):
        return self


class TemperatureResource(Resource):
    def __init__(self, name="TempJson", coap_server=None):
        super(TemperatureResource, self).__init__(name, coap_server, visible=True, observable=True,
                                                       allow_children=True)
        self.coap_server = coap_server
        self.lock = threading.Lock()
        self._content_type = "application/json"
        self.temperature = 0
        self.now = 0
        self.value = [{"name": self.name, "value": self.temperature, "time": self.now}]
        periodic_read(self, (23, 27))

    def render_GET_advanced(self, request, response):
        response.payload = self.payload
        response.code = defines.Codes.CONTENT.number
        return self, response



class DoorResource(Resource):
    def __init__(self, name="door", coap_server=None):
        super(DoorResource, self).__init__(name, coap_server, visible=True,
                                            observable=False, allow_children=True)
        self.coap_server = coap_server
        self.payload = "OPEN"
        self.content_type = "text/plain"

    def render_GET(self, request):
        return self

    # Query example: coap://0.0.0.0:5683/living_room/door?status=CLOSED
    def render_PUT_advanced(self, request, response):
        assert(isinstance(response, Response))
        if not str(request.uri_query):
            response.payload = "PUT: query is empty"
            response.code = defines.Codes.BAD_REQUEST.number
            return self, response

        # Convert the query string into a key,value dictionary
        query = urlparse(request.uri_query.lower()).path.split('&')
        query_dict = {q[:q.index("=")]: q[q.index("=")+1:] for q in query}

        if not set(query_dict).issubset(VALID_DOOR_QUERY):
            response.payload = "PUT: invalid query key"
            response.code = defines.Codes.BAD_REQUEST.number
            return self, response

        for key, val in query_dict.items():
            print(key, val)
            new_status = dispatch_query(key, val.upper())
            print(new_status)
            if new_status == "ERROR":
                response.payload = "PUT: invalid query value"
                response.code = defines.Codes.BAD_REQUEST.number
                return self, response
            else:
                self.payload = new_status

        response.payload = "Response changed through PUT"
        response.code = defines.Codes.CHANGED.number
        return self, response

    # Query example: coap://0.0.0.0:5683/living_room/door?create    + Payload w/ name of new resource
    def render_POST_advanced(self, request, response):
        print(self.__dict__)
        assert(isinstance(response, Response))
        if not str(request.uri_query):
            response.payload = "POST: query is empty"
            response.code = defines.Codes.BAD_REQUEST.number
            return self, response

        if not request.payload:
            response.payload = "POST: payload is empty"
            response.code = defines.Codes.BAD_REQUEST.number
            return self, response

        query = urlparse(request.uri_query.lower()).path

        if query.lower() not in VALID_POST:
            response.payload = "POST: invalid query"
            response.code = defines.Codes.BAD_REQUEST.number
            return self, response

        res_name = request.payload
        self.coap_server.add_resource(self.path+"/"+res_name, DoorResource(coap_server=self.coap_server,
                                                                        name=res_name))
        response.payload = "POST: created resource "+res_name
        response.code = defines.Codes.CREATED.number
        return self, response

    def render_DELETE_advanced(self, request, response):
        response.payload = "Response deleted"
        response.code = defines.Codes.DELETED.number
        return True, response



class BasicResource(Resource):
    def __init__(self, name="BasicResource", coap_server=None):
        super(BasicResource, self).__init__(name, coap_server, visible=True,
                                            observable=False, allow_children=True)

        self.payload = dispatch_query(self.name, None)
        self.resource_type = "rt1"
        self.content_type = "text/plain"
        self.interface_type = "if1"

    def render_GET(self, request):
        return self

    def render_PUT(self, request):
        self.edit_resource(request)
        return self

    def render_POST(self, request):
        res = self.init_resource(request, BasicResource())
        print(res, res.__dict__)
        return res

    def render_DELETE(self, request):
        return True


class Hello(Resource):
    def __init__(self, name="Hello", coap_server=None):
        super(Hello, self).__init__(name, coap_server, visible=True, observable=False, allow_children=False)
        self.content_type = "text/plain"

        self.payload = "HelloFriend"

    def render_GET(self, request):
        return self


class HelloPost(Resource):
    def __init__(self, name="HelloPost", coap_server=None):
        super(HelloPost, self).__init__(name, coap_server, visible=True, observable=False, allow_children=False)
        self.content_type = "text/plain"

        self.payload = "Hello Friend"

    def render_GET(self, request):
        return self

    def render_POST(self, request):
        self.edit_resource(request)
        return self

    def render_PUT(self, request):
        self.edit_resource(request)
        return self


class XMLResource(Resource):
    def __init__(self, name="XML"):
        super(XMLResource, self).__init__(name)
        self.value = 0
        self.payload = (defines.Content_types["application/xml"], "<value>" + str(self.value) + "</value>")

    def render_GET(self, request):
        return self


class MultipleEncodingResource(Resource):
    def __init__(self, name="MultipleEncoding"):
        super(MultipleEncodingResource, self).__init__(name)
        self.value = 0
        self.payload = str(self.value)
        self.content_type = [defines.Content_types["application/xml"], defines.Content_types["application/json"]]

    def render_GET(self, request):
        if request.accept == defines.Content_types["application/xml"]:
            self.payload = (defines.Content_types["application/xml"], "<value>" + str(self.value) + "</value>")
        elif request.accept == defines.Content_types["application/json"]:
            self.payload = (defines.Content_types["application/json"], "{'value': '" + str(self.value) + "'}")
        elif request.accept == defines.Content_types["text/plain"]:
            self.payload = (defines.Content_types["text/plain"], str(self.value))
        return self

    def render_PUT(self, request):
        self.edit_resource(request)
        return self

    def render_POST(self, request):
        res = self.init_resource(request, MultipleEncodingResource())
        return res


class AdvancedResource(Resource):
    def __init__(self, name="Advanced", coap_server=None, obs=True):
        super(AdvancedResource, self).__init__(name, coap_server, visible=True,
                                            observable=obs, allow_children=True)

        self.timer = threading.Timer(random.uniform(3.0, 10.9), self.periodic_read)
        self.periodic_read()

    def periodic_read(self):
        self.payload = read_temperature()
        if not self._coap_server.stopped.isSet():
            self.timer.setDaemon(True)
            self.timer.start()

            if self._coap_server._observeLayer._relations and self._coap_server is not None:
                self._coap_server.notify(self)
                self.observe_count += 1

    def render_GET_advanced(self, request, response):
        response.payload = self.payload
        response.code = defines.Codes.CONTENT.number
        return self, response
