import requests
import json
ip = '192.168.6.17'
# url = 'http://'+ip+':5000/api/post_alert'
# data = {'alert': 1}  # Dữ liệu gửi đi

# response = requests.post(url, json=data)
# print(response.json())  # Phản hồi từ API


# url = 'http://'+ip+':5000/api/lock/unlock'

# response = requests.post(url)
# print(response)  # Phản hồi từ API


####################################################

api_url = 'http://'+ip+':5000/api/account/add'
api_url = 'http://'+ip+':5000/api/account/lay-maxacnhan'
api_url = 'http://'+ip+':5000/api/account/kt-maxacnhan'
api_url = 'http://'+ip+':5000/api/account/capnhat-matkhau'
# api_url = 'http://'+ip+':5000/api/account/data'
# api_url = 'http://'+ip+':5000/api/account/login'
# # Dữ liệu tài khoản mới
# data = {
    # 'key': '5c1f45bde9d2aff92e03acbac0b6d49f6410ca490c1fe85a082650ee9c23f63d',
    # 'username': 'vbnm',
    # 'password': '12345678',
    # 'email': 'vbnm@gmail.com',
    # 'mobile': '032145687',
    # 'maxacnhan': '522526',
    # 'matkhaumoi': '546498436'
#     # 'fullname': 'Le Van A'
    # 'ten_tai_khoan_email_sdt': 'vbnm',
# }
# response = requests.post(api_url, json=data)
# print(response.json())  # Phản hồi từ API

# ####################################################

api_url = 'http://'+ip+':5000/api/lock/get-accesstoken'

response = requests.post(api_url)
print(response.text)  # Phản hồi từ API

api_url = 'http://'+ip+':5000/api/lock/unlock'

data = {
    'access_token': response.text
}
response = requests.post(api_url, json=data)
print(response.json())  # Phản hồi từ API

# ####################################################

# api_url = 'http://'+ip+':5000/api/ads/banner-img'

# # Dữ liệu tài khoản mới
# data = {
#     'email': 'chauchau@gmail.com',
#     'matkhaumoi': 'adudu'
# }
# response = requests.get(api_url)
# print(response.text)  # Phản hồi từ API