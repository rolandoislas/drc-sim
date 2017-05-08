class StatusSendingThread:
    def __init__(self):
        """
        Helper for registering callback status.
        """
        self.status_change_listeners = []
        self.status = None

    def set_status(self, status):
        """
        Set and notify callbacks if the status does not match the current status.
        :param status: status message
        :return: None
        """
        if self.status != status:
            self.status = status
            for listener in self.status_change_listeners:
                listener(status)

    def get_status(self):
        """
        Status getter
        :return: status string
        """
        return self.status

    def add_status_change_listener(self, callback):
        """
        Add a callback that will be called on status change.
        :param callback: callable function
        :return: None
        """
        self.status_change_listeners.append(callback)

    def clear_status_change_listeners(self):
        """
        Cleat the status callbacks.
        :return: None
        """
        self.status_change_listeners = []
