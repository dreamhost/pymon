import dispatch

from twisted.python import log

from pymon import utils

class ThresholdRules(object):
    # XXX need checks for state and separate checks for
    # notification
    # XXX generalize threshold checks here... how much of this
    # really should be in workflow?
    # XXX what about escalation? Which messages are sent? How are
    # messages sent? When are they NOT sent? Who gets what?

    def getOkThreshold(self):
        if self.factory.service_cfg.ok_threshold:
            return self.factory.service_cfg.ok_threshold
        else:
            return self.factory.type_defaults.ok_threshold

    def getWarnThreshold(self):
        if self.factory.service_cfg.warn_threshold:
            return self.factory.service_cfg.warn_threshold
        else:
            return self.factory.type_defaults.warn_threshold

    def getErrorThreshold(self):
        if self.factory.service_cfg.error_threshold:
            return self.factory.service_cfg.error_threshold
        else:
            return self.factory.type_defaults.error_threshold

    def setType(self, type):
        self.threshold_type = type

    def check(self, datum):
        log.msg("Got check data '%s'." % datum, debug=True)
        if self.isIn(datum, self.getOkThreshold()):
            log.msg("Status data is in 'ok' threshold.", debug=True)
            status = self.factory.statedefs.ok
            # The 'current status' index hasn't been updated yet, so 
            # 'current status' is really 'last status', and 'last status'
            # is really the run prior to last.
            if self.factory.state.get('current status') not in (
                self.factory.statedefs.ok,
                self.factory.statedefs.recovering):
                status = self.factory.statedefs.recovering
            self.status = status
        elif self.isIn(datum, self.getWarnThreshold()):
            log.msg("Status data is in 'warn' threshold.", debug=True)
            self.status = self.factory.statedefs.warn
        elif self.isIn(datum, self.getErrorThreshold()):
            log.msg("Status data is in 'error' threshold.", debug=True)
            self.status = self.factory.statedefs.error
        elif datum == self.factory.statedefs.failed:
            self.status = self.factory.statedefs.failed
        else:
            self.status = self.factory.statedefs.unknown

    [ dispatch.generic() ]
    def isIn(self, datum, threshold):
        '''
        Generic method for checking data against thresholds
        '''

    [ isIn.when("self.threshold_type == 'ranged'") ]
    def rangedIsIn(self, datum, threshold):
        log.msg("Using dispatch method 'rangedIsIn'...", debug=True)
        log.msg("datum: %s" % datum, debug=True)
        log.msg("datum type: %s" % type(datum), debug=True)
        log.msg("threshold: %s" % threshold, debug=True)
        log.msg("threshold type: %s" % type(threshold), debug=True)
        if datum in threshold:
            return True
        else:
            return False

    [ isIn.when("self.threshold_type == 'listed'") ]
    def listedIsIn(self, datum, threshold):
        log.msg("Using dispatch method 'listedIsIn'...", debug=True)
        if datum in threshold:
            return True
        return False

    [ isIn.when("self.threshold_type == 'exact'") ]
    def isExactly(self, datum, threshold):
        log.msg("Using dispatch method 'isExactly'...", debug=True)
        if str(datum) == threshold:
            return True
        return False

    def isMessage(self):
        if self.status == self.factory.statedefs.ok:
            return False
        return True

    def setMsg(self, *args):
        self.msg = self.factory.type_defaults.message_template % args

    def setSubj(self, *args):
        status = utils.getStateNameFromNumber(self.status)
        if status == 'unknown':
            self.subj = "Unknown status"
        else:
            msg = getattr(self.factory.type_defaults, '%s_message' % status)
            self.subj = msg % args

    def sendIt(self):
        from pymon.message import LocalMail

        if self.status == self.factory.statedefs.recovering:
            status_id = self.factory.state.get('current status')
            status = utils.getStateNameFromNumber(status_id)
            self.msg = self.msg + "\r\nRecovering from '%s'." % status
        cfg = self.factory.service_cfg
        sendmail = self.factory.cfg.sendmail
        frm = self.factory.cfg.mail_from
        # XXX we probably want to make the actual sending of emails
        # non-blocking. Dererreds anyone?
        # XXX modify this when support for escalation and different 
        # group levels is added to python
        for address in utils.getMailList(self.factory.uid):
            email = LocalMail()
            email.setSendmailBinary(sendmail)
            email.setSubject(self.subj)
            email.setTo(address)
            email.setFrom(frm)
            email.setData(self.msg)
            email.send()
            print self.factory.type_defaults.sent_message % address  
