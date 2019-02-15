from qem_setter import QemSetter
import time

setter = QemSetter()

setter.setResistorValue('VCM', 2)
setter.setResistorRegister('auxsample', 50)
setter.changeDefaults(True)
setter.setClock(25)

while True:
    for i in range(-10, 10):
        if i < 0:
            setter.setResistorValue('VCTRL', (3 + (.5 * i)))
        else:
            setter.setResistorValue('VCTRL', (3 - (.5 * i)))
        time.sleep(2)
        
