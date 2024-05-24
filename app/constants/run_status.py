class RunStatus:
    NEW = 1
    SLEEPING = 2
    WORKING = 3
    FINISHED = 4
    FAILED = 5

    @classmethod
    def get_list(cls):
        return {
            'status': [
                (cls.NEW, 'New'),
                (cls.SLEEPING, 'Sleeping'),
                (cls.WORKING, 'Working'),
                (cls.FINISHED, 'Finished'),
                (cls.FAILED, 'Failed'),
            ]
        }
