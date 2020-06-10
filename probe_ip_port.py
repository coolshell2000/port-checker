import socket
import telnetlib
import datetime
import pprint
import sys

import json


class ProbeHost:
    def __init__(self, d_target_host_payload, verbose=0):
        
        #print("d_target_host_payload:{}".format(d_target_host_payload))
        if "name" not in d_target_host_payload.keys():
            d_target_host_payload["name"] = "noname"
            
        self.verbose = verbose
        
        self.d_target_host_combined = {"payload": d_target_host_payload, "result": {}}

        try:
            self.d_target_host_combined["payload"]["reverse_dns"] = \
                socket.gethostbyaddr(self.d_target_host_combined["payload"]["address"])[0]  # ('google-public-dns-a.google.com', [], ['8.8.8.8'])
        except Exception as e:
            #print("Exception: e:{}".format(str(e)))
            self.d_target_host_combined["payload"]["reverse_dns"] = "reverse_dns_failed"
            # self.d_target_host_combined["result"]["target_brief_str"] = \
            #     self.d_target_host_combined["result"]["target_brief_str"] + exec_str
            pass
        
        self.d_target_host_combined["result"]["target_brief_str"] = \
            "{0:30}{1:20}{2} @ {3}".format(self.d_target_host_combined["payload"]["name"],
                                         self.d_target_host_combined["payload"]["address"],
                                         self.d_target_host_combined["payload"]["ports"],
                                         self.d_target_host_combined["payload"]["reverse_dns"])
    
    def get_result_as_json(self):
    
        # import json
        #
        # r = {'is_claimed': 'True', 'rating': 3.5}
        # r = json.dumps(r)
        # loaded_r = json.loads(r)
        # loaded_r['rating']  # Output 3.5
        # type(r)  # Output str
        # type(loaded_r)  # Output dict

        return json.dumps(self.d_target_host_combined)
        
    # method to fill d_port_result and return
    def probe_via_telnet(self):  # this timeout is used for init the telnet object and the follow up read port
        
        ts_start = datetime.datetime.now()
        
        tn_expect_str = "ssh333"
        tn_expect_str_as_bytes = str.encode(tn_expect_str)
    
        if self.verbose > 0:
            print(self.d_target_host_combined["result"]["target_brief_str"])
            print()
        for port in self.d_target_host_combined["payload"]["ports"]:
            try:
                with telnetlib.Telnet(host=self.d_target_host_combined["payload"]["address"],
                                      port=port,
                                      timeout=self.d_target_host_combined["payload"]["timeout"]) as tn:
                    if self.verbose > 0:
                        print("{}\t{}\t\tconnection ok.\t\t\treading..".format(self.d_target_host_combined["payload"]["address"],
                                                                               port),
                              end="")
                    result_ru = tn.read_until(tn_expect_str_as_bytes,
                                              timeout=self.d_target_host_combined["payload"]["timeout"]).decode("utf-8")
                    if len(result_ru) < 1:
                        result_ru = "empty is also all-right"
                    self.d_target_host_combined["result"][str(port)] = result_ru
                    tn.close()  # can skip this as using the with clause will ensure close when block done.
                    if self.verbose > 0:
                        if len(result_ru) > 64:
                            print("\tok. {}...".format(result_ru[0:63]))
                        else:
                            print("\tok. {}".format(result_ru[0:63]))
                    continue
            except Exception as e:
                exec_str = "{}\t{}\t\tEXCEPTION AT CONNECTION!\t{}\t{}"\
                    .format(self.d_target_host_combined["payload"]["address"], port,
                            str(e), datetime.datetime.now())
                if self.verbose > 0:
                    print(exec_str)
                self.d_target_host_combined["result"][str(port)] = None
                self.d_target_host_combined["result"]["target_brief_str"] = \
                    self.d_target_host_combined["result"]["target_brief_str"] + exec_str
                continue
                pass
        
        if self.verbose > 0:
            print()
            print(datetime.datetime.now())
        
        ts_end = datetime.datetime.now()
        payload_cost_in_seconds = (ts_end - ts_start).seconds
        self.d_target_host_combined["result"]["payload_cost_in_seconds"] = payload_cost_in_seconds
        
        return self.d_target_host_combined


def main(argv):
    target_host4 = {"address": "www.google9993333.com", "ports": [443, 99, 33, 77],
                    "timeout": 1}  # longer timeout for low/faraway hosts
    
    prober = ProbeHost(target_host4, verbose=2)
    
    d_result_combined = prober.probe_via_telnet()
    
    print("\nd_result_combined:{}".format(d_result_combined))
    pprint.pprint(d_result_combined)

    
if __name__ == "__main__":
    main(sys.argv)

