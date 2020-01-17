#!/usr/bin/env python

import getopt
import sys
from coapthon.server.coap import CoAP
from resources import BasicResource, BasicTemperatureResource, TemperatureResource, Hello, DoorResource, \
    ObservableResource, HelloPost, AdvancedResource


class CoAPServer(CoAP):
    def __init__(self, host, port, multicast=False):
        CoAP.__init__(self, (host, port), multicast)
        self.add_resource('basic/', BasicResource())
        self.add_resource('hello_world/', Hello())
        self.add_resource('hello_post/', HelloPost())
        self.add_resource('living_room/', BasicResource(coap_server=self))
        self.add_resource('living_room/temperature', BasicTemperatureResource(coap_server=self))
        self.add_resource('living_room/door', DoorResource(coap_server=self, name="living_room_door"))
        self.add_resource('dinning_room/', BasicResource(coap_server=self))
        self.add_resource('dinning_room/temperature', TemperatureResource(coap_server=self, name='dinning'))
        self.add_resource('dinning_room/door', DoorResource(coap_server=self, name="dinning_room_door"))
        self.add_resource('main_door', DoorResource(coap_server=self, name="main_door"))
        self.add_resource('test', AdvancedResource(coap_server=self, name="test"))

        print("CoAP Server start on " + host + ":" + str(port))
        print(self.root.dump())


def usage():  # pragma: no cover
    print("coapserver.py -i <ip address> -p <port>")


def main(argv):  # pragma: no cover
    ip = "0.0.0.0"
    port = 5683
    multicast = False
    try:
        opts, args = getopt.getopt(argv, "hi:p:m", ["ip=", "port=", "multicast"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt in ("-i", "--ip"):
            ip = arg
        elif opt in ("-p", "--port"):
            port = int(arg)
        elif opt in ("-m", "--multicast"):
            multicast = True

    server = CoAPServer(ip, port, multicast)
    try:
        server.listen(10)
    except KeyboardInterrupt:
        print("Server Shutdown")
        server.close()
        print("Exiting...")


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
