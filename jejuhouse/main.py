
from classes.oiljang import OilJang
from classes.kyocharo import Kyocharo

o = OilJang()
o_data = o.get_data()

k = Kyocharo()
k_data = k.get_data()

data = {'오일장': o_data, '교차로': k_data}
print(data)
print(len(data['오일장']))
print(len(data['교차로']))
