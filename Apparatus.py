import Devices


class apparatus(dict):
    def __init__(self):
        dict.__init__(self)
        self['devices'] = {}
        self['calibrations'] = {}
        self['information'] = {}
        self['eproclist'] = []
        self.proclog = []
        self.proclog_threadindex = 0
        self.proclog_depthindex = 0
        self.executor = ''
        self.simulation = False
        self.dependent_Devices = []

    def Connect_All(self, executor, simulation=False):
        self.simulation = simulation
        self.executor = executor

        for device in self['devices']:
            self['devices'][device]['Connected'] = False

            if self['devices'][device]['addresstype'] == 'pointer':
                # Create instance of the Device
                self['devices'][device]['address'] = getattr(Devices, self['devices'][device]['type'])(device)

                # Register the device with the Executor
                self['devices'][device]['address'].ERegister(executor)

                # Add Device descriptors to Apparatus ones
                if 'descriptors' in self['devices'][device] and type(self['devices'][device]['descriptors']) == list:
                    self['devices'][device]['descriptors'] = [*self['devices'][device]['descriptors'],
                                                              *self['devices'][device]['address'].descriptors]
                else:
                    self['devices'][device]['descriptors'] = self['devices'][device]['address'].descriptors

                # Set Device simulation state
                self['devices'][device]['address'].simulation = simulation

                # Check if the device is dependent on other devices and conncect if not dependent
                if self['devices'][device]['address'].dependent_device:
                    # Add to dependent device list for later processing
                    self.dependent_Devices.append(device)
                else:
                    self.Connect(device)

                # Connect the dependent devices
                self.Dep_Connects()

    def Connect(self, deviceName, executor=''):
        # use default executor if none is given
        if executor == '':
            executor = self.executor

        # Get Arguments of Connect for the device
        self['devices'][deviceName]['address'].CreateEprocs(self, self.executor)
        deviceconnect = self.GetEproc(deviceName, 'Connect')
        arguments = list(deviceconnect.requirements)

        # Try to collect the required arguments together
        details = {}
        for element in arguments:
            if element != '':
                try:
                    details[element] = self['devices'][deviceName][element]
                except KeyError:
                    errorstr = element + ' missing. Insuffienct information to connect.'
                    raise Exception(errorstr)

        # Run the Connect method of the Device with the right arguments
        deviceconnect.Do(details)

        # Note in the apparatus that the device is connected
        self['devices'][deviceName]['Connected'] = True

    def Dep_Connects(self):
        loopcounter = 0

        while len(self.dependent_Devices) > 0:
            device = self.dependent_Devices.pop(0)
            Ready2Connect = True

            for devname in self['devices'][device]['address'].dependencies:
                parent_devname = self['devices'][device][devname+'name']

                if self['devices'][parent_devname]['Connected']:
                    self['devices'][device][devname + 'address'] = self['devices'][parent_devname]['address']
                else:
                    Ready2Connect = False

            if Ready2Connect:
                self.Connect(device)
                loopcounter = 0
            else:
                self.dependent_Devices.append(device)

            loopcounter += 1
            if len(self.dependent_Devices) != 0 and loopcounter > 4 * len(self.dependent_Devices):
                raise Exception('Dependencies not found')

    def Disconnect(self):
        if not self.simulation:
            for device in self['devices']:
                if self['devices'][device]['addresstype'] == 'pointer':
                    self['devices'][device]['address'].Disconnect()

    def getValue(self, infoAddress):
        if infoAddress == '':
            return ''

        level = self

        for branch in infoAddress:
            try:
                level = level[branch]
            except TypeError:
                return 'Invalid ApparatusAddress'
            except KeyError:
                return 'Invalid ApparatusAddress'

        return level

    def findDevices(self, key, value=[]):
        foundDevices = []

        for device in self['devices']:
            devicePasses = True

            if key not in self['devices'][device]:
                devicePasses = False
            else:
                if value != []:
                    if type(self['devices'][device][key]) == dict or type(self['devices'][device][key]) == list:
                        if value not in self['devices'][device][key]:
                            devicePasses = False

                    elif self['devices'][device][key] != value:
                        devicePasses = False

            if devicePasses:
                foundDevices.append(device)

        return foundDevices

    def findDevice(self, reqs):
        devicesOld = ''
        devicesNew = []
        devicesTemp = []
        requirements = []

        for req in reqs:
            if type(reqs[req]) == list:
                for element in reqs[req]:
                    requirements.append([req, element])
            else:
                requirements.append([req, reqs[req]])

        for line in requirements:
            devicesNew = self.findDevices(line[0], line[1])

            if devicesOld == '':
                devicesOld = devicesNew
            else:
                devicesTemp = devicesOld[:]

                for device in devicesOld:
                    if device not in devicesNew:
                        devicesTemp.remove(device)

                devicesOld = devicesTemp[:]

        if len(devicesOld) == 1:
            return devicesOld[0]
        elif len(devicesOld) > 1:
            return 'More than 1 device met requirments.' + str(devicesOld)
        elif len(devicesOld) == 0:
            return 'No devices met requirments'

    def GetEproc(self, device, method):
        for line in self['eproclist']:
            if line['device'] == device and line['method'] == method:
                return line['handle']

        return 'No matching elemental procedure found.'

    def LogProc(self, procName, information):
        if information == 'start':
            self.proclog_depthindex += 1
        elif information == 'end':
            self.proclog_depthindex -= 1
        else:
            info = self.buildInfoEntry(information)
            procLogLine = []

            for n in range(self.proclog_depthindex):
                procLogLine.append('->')

            procLogLine.append({'name': procName, 'information': info})
            self.proclog.append(procLogLine)

    def buildInfoEntry(self, information):
        simpleinfo = {}

        if type(information) == str:
            simpleinfo = information
        elif type(information) == dict:
            for info in information:
                if type(information[info]['value']) in [dict, list, int, float, str]:
                    simpleinfo[info] = information[info]['value']
                else:
                    simpleinfo[info] = type(information[info])

        return simpleinfo
