from classes.auction import Auction
from classes.blog import NaverBlog
from classes.oiljang import OilJang
from classes.kyocharo import Kyocharo

a = Auction()
a_data = a.get_data()

b = NaverBlog()
b_data = b.get_data()

o = OilJang()
o_data = o.get_data()

k = Kyocharo()
k_data = k.get_data()



data = {'온비드' : a_data, '네이버블로그' : b_data, '오일장': o_data, '교차로': k_data}
print(data)

