import logging
import sys
import droneapp.controllers.server

import droneapp.controllers.server

# membuat log data
logging.basicConfig(level=logging.INFO,
                    stream=sys.stdout
                    )

if __name__ == '__main__':
    droneapp.controllers.server.run()