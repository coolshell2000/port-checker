import sys, os
import datetime
import pprint
from util.email_noti.email_notification import EmailNotification
from probe_ip_port import ProbeHost
import json
import argparse
import logging
from logging.handlers import RotatingFileHandler
from configparser import ConfigParser


def create_rotating_log(path):
    """
    Creates a rotating log
    """
    logger = logging.getLogger("Rotating Log")
    logger.setLevel(logging.DEBUG)
    
    # add a rotating handler
    handler = RotatingFileHandler(path, maxBytes=20000,
                                  backupCount=3)
    # create formatter
    formatter = logging.Formatter\
        ('[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s', "%Y-%m-%d_%a_%H:%M:%S")
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


parser = argparse.ArgumentParser()  # (description='grabbing slots')

### args for portchecker

parser.add_argument('-payload', type=str, nargs=1, default=['hosts_to_check_test.json'],
                    help='path to json file containing the hosts/payload to scan')

parser.add_argument('-filter', type=str, nargs=1, default=[''],
                    help='filter_case_insensitive, will be applied to brief str constructed from the server json')

parser.add_argument('-notify_email', type=str, nargs=1, default=["ggs.alfa.2015@gmail.com"],
                    help='notify by email given if any port of any server failed test. '
                         'todo: can also use email specified in payload json, for per server/port notify')

parser.add_argument('-verbose', type=int, nargs=1, choices=[0, 1, 2, 3], default=[0],
                    help='show verbose information at specified level. 0 is nothing to show')

parser.add_argument('-rest_url', type=str, nargs=1, default=[""],
                    help="post json(d_result_combined) to restful server's endpoint specified by this url"
                         "normally a mongodb agent")

args = parser.parse_args()

# create a rotation log
log_file = "private.ed/log/"+os.path.basename(sys.argv[0]) + '.log'
logger_rota = create_rotating_log(log_file)
logger_rota.debug("start...")

# create an instance of ConfigParser class.
parser = ConfigParser()
parser.read('/home/bt/ggs.ini')
imap_passwd_ggs_alfa_2015 = parser.get('gdata', 'IMAP_PASSWD_ggs_alfa_2015')

# name_from = "ggs.alfa.2015"
# email_from = "ggs.alfa.2015@gmail.com"

# need to enable less secure in gmail settings, otherwise auth error
email_notifier = EmailNotification(smtp="smtp.gmail.com", login="ggs.alfa.2015",
                                   password=imap_passwd_ggs_alfa_2015, port=587, logger=logger_rota)

# email_notifier = EmailNotification(name_from=getpass.getuser() + "@" + socket.gethostname(),
#                                    email_from=getpass.getuser() + "@" + socket.gethostname())
# email_notifier = EmailNotification()  # default paras moved to lib class


path_hosts_json_file = args.payload[0]
logger_rota.info("reading in targeting hosts/payloads from {}".format(path_hosts_json_file))
with open(path_hosts_json_file, "r") as read_file:
    list_targets = json.load(read_file)

logger_rota.info("filtering out unwanted targets.. by filter:{}".format(str(filter)))
list_targets_filtered = []
for d_target in list_targets:
    if args.filter[0].lower() in str(d_target.values()).lower():
        list_targets_filtered.append(d_target)

logger_rota.info("{} filtered targets. starting ...".format(len(list_targets_filtered)))

#
# with open('hosts_to_check_from_d7.json', 'w') as fp:
#     json.dump(targets, fp)  ################## dump for dict, dumps for list of dicts,

counter = 0
counter_ok = 0
d_errors = {} # key is target_brief_str, value is d_result_combined
for d_target_host in list_targets_filtered:
    
    prober = ProbeHost(d_target_host_payload=d_target_host, verbose=args.verbose[0])
    target_brief_str = prober.d_target_host_combined["result"]["target_brief_str"]
    
    logger_rota.info("\n{}. {}".format(counter, target_brief_str))
    
    #### payload ####
    d_result_combined = prober.probe_via_telnet()
    #################
    
    if None in d_result_combined["result"].values():
        logger_rota.error("error\t{}".format(target_brief_str))
        logger_rota.error(d_result_combined)
        logger_rota.error("to send email when loop finishes")
        d_errors[target_brief_str] = d_result_combined
        # list_target_brief_str.append(target_brief_str)
        # list_d_result_combined.append(d_result_combined)
    else:
        logger_rota.info("okay")
        counter_ok = counter_ok + 1
    
    if args.verbose[0] > 1:
        print("\njson - d_result_combined:")
        json_str = prober.get_result_as_json()
        pprint.pprint(json_str)
    
    counter = counter + 1

if counter > 0:
    logger_rota.info("{:.2f}% okay on {} of {} nodes filtered by {}"
                     .format(counter_ok/counter*100, counter_ok, counter, str(args.filter)))
    if counter_ok < counter:
        email_notifier.send_email(args.notify_email[0], subject=str(args.filter), msg=str(d_errors))
