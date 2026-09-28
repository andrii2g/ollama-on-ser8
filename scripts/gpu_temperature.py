"""Read GPU temperature without installing a sensor service.
Windows: D3DKMT_ADAPTER_PERFDATA.Temperature (0.1 C), query type 62.
https://learn.microsoft.com/windows-hardware/drivers/ddi/d3dkmthk/ns-d3dkmthk-_d3dkmt_adapter_perfdata
Linux: amdgpu hwmon temperature inputs. Returns the hottest available GPU sensor.
"""
import ctypes as c
import os
from pathlib import Path


def gpu_temperature():
    if os.name != 'nt':
        readings = []
        for device in Path('/sys/class/hwmon').glob('hwmon*'):
            if (device / 'name').read_text().strip() == 'amdgpu':
                readings.extend(float(p.read_text()) / 1000 for p in device.glob('temp*_input'))
        return max(readings) if readings else None

    class Luid(c.Structure):
        _fields_ = [('low', c.c_uint32), ('high', c.c_int32)]
    class Adapter(c.Structure):
        _fields_ = [('handle', c.c_uint32), ('luid', Luid), ('sources', c.c_uint32), ('precise', c.c_int32)]
    class Enum(c.Structure):
        _fields_ = [('count', c.c_uint32), ('adapters', c.POINTER(Adapter))]
    class Perf(c.Structure):
        _fields_ = [('index', c.c_uint32)] + [(n, c.c_uint64) for n in ('memory_freq', 'max_freq', 'max_oc', 'bandwidth', 'pcie')] + [(n, c.c_uint32) for n in ('fan', 'power', 'temperature')] + [('powerstate', c.c_ubyte)]
    class Query(c.Structure):
        _fields_ = [('handle', c.c_uint32), ('type', c.c_int32), ('data', c.c_void_p), ('size', c.c_uint32)]

    gdi = c.WinDLL('gdi32')
    adapters = (Adapter * 16)()
    enumeration = Enum(16, adapters)
    if gdi.D3DKMTEnumAdapters2(c.byref(enumeration)) != 0:
        return None
    readings = []
    for adapter in adapters[:enumeration.count]:
        try:
            perf = Perf()
            query = Query(adapter.handle, 62, c.addressof(perf), c.sizeof(perf))
            if gdi.D3DKMTQueryAdapterInfo(c.byref(query)) == 0 and 0 < perf.temperature < 1500:
                readings.append(perf.temperature / 10)
        finally:
            handle = c.c_uint32(adapter.handle)
            gdi.D3DKMTCloseAdapter(c.byref(handle))
    return max(readings) if readings else None


if __name__ == '__main__':
    print(gpu_temperature())
