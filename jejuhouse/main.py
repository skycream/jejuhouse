from classes.auction import Auction
from classes.blog import NaverBlog
from classes.oiljang import OilJang
from classes.kyocharo import Kyocharo

import json

def format_data(o_data, k_data):
    data = {'오일장': o_data, '교차로': k_data}
    formatted_json = json.dumps(data, ensure_ascii=False, indent=2)
    print(formatted_json)

# a = Auction()
# a_data = a.get_data()

# b = NaverBlog()
# b_data = b.get_data()

o = OilJang()
o_data = o.get_data()

k = Kyocharo()
k_data = k.get_data()



data = {'오일장': o_data, '교차로': k_data}
format_data(o_data, k_data)
