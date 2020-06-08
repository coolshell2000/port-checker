#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Python 3 and compatibility with Python 2
from __future__ import unicode_literals, print_function

import os
import sys
import re
import logging
from logging.handlers import RotatingFileHandler
import time
import socket, getpass

import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from jinja2 import Environment, FileSystemLoader


class EmailNotification(object):
    EMAIL_REGEX = re.compile('([\w\-\.\']+@(\w[\w\-]+\.)+[\w\-]+)')
    HTML_REGEX = re.compile('(^<!DOCTYPE html.*?>)')
    
    # default as gmail outgoing mail (SMTP) server	smtp.gmail.com Requires SSL: Yes Requires TLS: Yes (if available) Requires Authentication: Yes Port for SSL: 465 Port for TLS/STARTTLS: 587
    # passwd masked, to supply or move to .ini
    def __init__(self,
                 name_from=getpass.getuser() + "@" + socket.gethostname(),
                 email_from=getpass.getuser() + "@" + socket.gethostname(),
                 smtp="smtp.gmail.com", login="ggs.alfa.2015",
                 password="kxxx", templatedir='templates', logger=None, port=587):
        self.logger = logger
        if not logger:
            logging.basicConfig()
            self.logger = logging.getLogger(__name__)
        self.smtp = smtp
        self.mfrom = "%s <%s>" % (name_from, email_from)
        # self.mfrom = "%s_at_%s <%s>".format(getpass.getuser(), socket.gethostname(), fromemail)
        self.reply = email_from
        self.smtplogin = login
        self.smtppass = password
        self.port = port
        if os.path.isdir(templatedir):
            self.templatedir = templatedir
        else:
            self.templatedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), templatedir)
        self.env = Environment(loader=FileSystemLoader(self.templatedir))
    
    def _mailrender(self, data, template):
        template = template + ".tmpl"
        self.logger.debug("Rendering template '%s'" % (template))
        text = self.env.get_template(template)
        msg = text.render(data)
        return msg
    
    def _smtpconnect(self):
        try:
            # smtp = smtplib.SMTP(self.smtp, port=25)
            smtp = smtplib.SMTP(self.smtp, port=self.port)
            
            # gmail port 587 need ehlo() and ttl
            if self.port != 25:
                smtp.ehlo()
                smtp.starttls()
        except Exception as e:
            self.logger.error("Cannot connect with '%s': %s" % (self.smtp, e))
            raise
        if self.smtplogin:
            try:
                # print(self.smtplogin, self.smtppass)
                smtp.login(self.smtplogin, self.smtppass)
            except smtplib.SMTPException as e:
                self.logger.error("Cannot auth with '%s' on %s: %s" % (self.smtplogin, self.smtp, e))
                raise
            # finally:
            #     smtp.quit()
        return smtp
    
    def _smtpsend(self, smtp, str_emails_to, subject, content):
        if self.HTML_REGEX.match(content) is None:
            self.logger.debug("Sending text mail to '%s'" % (str_emails_to))
            msg = MIMEText(content)
        else:
            self.logger.debug("Sending html mail to '%s'" % (str_emails_to))
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(content, 'html', 'utf-8'))
        msg['From'] = self.mfrom
        #print("name_to:{}, str_emails_to:{}".format(name_to, str_emails_to))
        #msg['To'] = "%s <%s>" % (name_to, email_to)
        msg['To'] = "<%s>" % (str_emails_to)
        msg['Reply-to'] = self.reply
        msg['Subject'] = subject

        # list_emails_to = []  # all cases covered below. so no need
        if ',' in str_emails_to:
            list_emails_to = str_emails_to.split(',')
        elif ';' in str_emails_to:
            list_emails_to = str_emails_to.split(';')
        else:
            list_emails_to = [str_emails_to]  # single email (indiv cases invoked from batch call), still need put into a list!
        
        print("final before sendmail. list_emails_to:{}".format(list_emails_to))
        smtp.sendmail(self.mfrom, list_emails_to, msg.as_string())
    
    def send_email(self, recipient, subject, msg):
        smtp = self._smtpconnect()
        try:
            self._smtpsend(smtp, recipient, subject, msg)
        except smtplib.SMTPException as e:
            self.logger.error("Cannot send mail to '%s': %s" % (recipient, e))
            raise
        finally:
            smtp.quit()
    
    def send_bulk(self, tasks):
        smtp = self._smtpconnect()
        processed = 0
        for (email_to, subject, msg_body_rendered_str) in tasks:
            try:
                self._smtpsend(smtp, email_to, subject, msg_body_rendered_str)
            except smtplib.SMTPException as e:
                self.logger.error("Cannot send mail to '%s': %s" % (email_to, e))
            else:
                processed += 1
        smtp.quit()
        return processed
    
    def mailout(self, email, name, subject, data, template):
        if email is None:
            error = "Email is empty!"
            self.logger.error(error)
            raise ValueError(error)
        elif self.EMAIL_REGEX.match(email) is None:
            error = "Invalid email address!"
            self.logger.error(error)
            raise ValueError(error)
        msg = self._mailrender(data, template)
        self.send_email(email, subject, msg)
    
    def mailbulk(self, email_data, template):
        elist = []
        for edata in email_data:
            try:
                # name_from = edata["name_from"]
                # email_from = edata["email_from"]
                # if name_from is None:
                #     name_from = email_from
                #
                email_to = edata["email_to"]
                # name_to = edata["name_to"]
                # if name_to is None:
                #     name_to = email_to
                subject = edata["subject"]
                body = edata["body"]
            except Exception as e:
                continue
            if email_to is None:
                error = "email_to is empty!"
                self.logger.error(error)
                continue
            elif self.EMAIL_REGEX.match(email_to) is None:
                error = "Invalid email_to address!"
                self.logger.error(error)
                continue
            msg_body_rendered_str = self._mailrender(body, template)
            # elist.append((name_from, email_from, name_to, email_to, subject, msg_body_rendered_str))
            elist.append((email_to, subject, msg_body_rendered_str))
        return self.send_bulk(elist)


# ---------end of class above

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
    formatter = logging.Formatter('[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger
    
    # for i in range(10):
    #     logger.info("This is test log line %s" % i)
    #     time.sleep(1.5)


def main(argv):
    # logging.basicConfig(filename=argv[0]+'.log', level=logging.DEBUG,
    #                    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
    #                    datefmt='%a %Y-%m-%dT%H:%M:%S')
    log_file = argv[0] + '.log'
    logger_rota = create_rotating_log(log_file)
    logger_rota.debug("start...")
    # use soton email to send
    # e = EmailNotification("smtp.soton.ac.uk", "bt", "bt@soton.ac.uk") # default port is 25 for soton outlook without using gmail.
    
    # create an instance of ConfigParser class.
    parser = ConfigParser()
    # parser.read(sys.argv[0].rsplit('.', 1)[0]+'_ggs'+'.ini')
    parser.read('/home/bt/ggs.ini')
    imap_passwd_ggs_alfa_2015 = parser.get('gdata', 'IMAP_PASSWD_ggs_alfa_2015')
    
    name_from = "ggs.alfa.2015"
    email_from = "ggs.alfa.2015@gmail.com"
    
    # need to enable less secure in gmail settings, otherwise auth error
    e = EmailNotification(name_from=name_from, email_from=email_from, smtp="smtp.gmail.com", login="ggs.alfa.2015",
                          password=imap_passwd_ggs_alfa_2015, port=587, logger=logger_rota)
    
    # this has problem ignoring receiptant apart from the first one!
    # fixed now. final smtp.sendmail() needs a single string or list [] if more than one recipients !
    e.send_email("bt2000@gmail.com, bt@soton.ac.uk", "single test", "single msg")
    print("single sent. continue testing bulk sending now.")
    # sys.exit(0)
    
    agent_str = getpass.getuser() + '@' + socket.gethostname()

    list_email_to = ["bt2000@gmail.com", "bt2000a@gmail.com"]
    list_name_to = ["unknown", "bt at gmail"]
    
    tasks_list2 = []
    for i in range(0, len(list_email_to)):
        email_to = list_email_to[i]
        if list_name_to[i] is None or len(list_name_to[i]) < 1 or "unknown" in list_name_to[i].lower():
            name_to = email_to.split('@')[0]
        else:
            name_to = list_name_to[i]
            
        tasks_list2.append(
            {
                "name_to": name_to,
                "email_to": email_to,
                "subject": "batch subject",
                "body": {
                    "dear": name_to,
                    "msg": "This is a <b>test</b>",
                    "name_from": name_from,
                    "agent": agent_str
                }
            }
        )
    
    num_processed = e.mailbulk(tasks_list2, "email-html_notify")
    print("{} emails have been processed/sent".format(num_processed))
    
    logger_rota.info("info test..")
    logger_rota.debug("finished...")


if __name__ == "__main__":
    main(sys.argv)
