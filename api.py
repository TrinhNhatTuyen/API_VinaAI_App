
from flask import Flask, request, jsonify, Response
import socket, pyodbc, random, time, os, cv2, base64, hashlib, time, requests, datetime, json
app = Flask(__name__)
value = None
random_banner = ''
current_banner = ''
banner_folder_path = 'banner'
cam_img_folder_path = 'cam_img'
#---------------------------------------------------------------------------------------------------
def connect_to_database():
    max_retries = 5
    retry_delay = 5  # Đợi 5 giây trước khi thử kết nối lại

    for retry_count in range(max_retries):
        try:
            conn = pyodbc.connect("Driver={SQL Server};"
                                  "Server=112.78.15.3;"
                                  "Database=VinaAIAPP;"
                                  "uid=ngoi;"
                                  "pwd=admin123;")
            print("Kết nối thành công!")
            return conn  # Trả về kết nối nếu thành công
        except pyodbc.OperationalError:
            if retry_count < max_retries - 1:
                print("Kết nối không thành công. Thử kết nối lại sau {} giây.".format(retry_delay))
                time.sleep(retry_delay)
            else:
                print("Không thể kết nối đến cơ sở dữ liệu sau nhiều lần thử. Đã đạt đến giới hạn thử lại.")
                raise

conn = connect_to_database()
cursor = conn.cursor()
#---------------------------------------------------------------------------------------------------
# Lấy địa chỉ IP của máy
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()
    return ip_address
ip_address = get_ip_address()
#---------------------------------------------------------------------------------------------------
api_keys = ['3ab281f56574187a64b1b9abfad4ea7fefe5ff89c4a47a0cf4d2782aa38248e7',
            '6768d2372a333a0230955442278719012d8ebdbd954c529cdc20c7d3955161aa',
            '5c1f45bde9d2aff92e03acbac0b6d49f6410ca490c1fe85a082650ee9c23f63d',
            '6ab6fda952f7ae1499f850c9bb18cc1a7515c595eec0787301b1c26a577a74c7',
            'fb4cc8fde5e512e3e994d99cd6d4e209289e32f53730a788fb59921e3446928f',
            '5cde773edc9baddf85682ae625f388b8a9b5e1bee398df72757a11801d2f4737',
            '960d65cfd84e76e43a89902fb842117b3a8352f8547b8ca4c5320564bef943bd',
            '1ccff985dea7c477c7678b6b9e34bbc073ed377953d631939c306c1c577a0659',
            '23da994e97602d5623df7232659fd61d6af8045cffe9992d4b96d4498cb25c7c',
            '0615e264fd806b2322ad3c1ae993306df2f082ba933052f628ba3b55314013ec']
#---------------------------------------------------------------------------------------------------

@app.route('/api/post_alert', methods=['POST'])
def receive_signal():
    global value
    data = request.json  # Nhận dữ liệu từ máy tính
    # Xử lý dữ liệu và trả về phản hồi
    value = data['alert']
    response = {'message': 'Received alert: ' + str(value)}
    return jsonify(response)

#---------------------------------------------------------------------------------------------------

@app.route('/api/get_alert', methods=['GET'])
def get_value():
    
    response = {'alert': value}
    return jsonify(response)

####################################################################################################

@app.route('/api/account/add', methods=['POST'])
def them_tai_khoan():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    # customerid = data.get('customerid')
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    mobile = data.get('mobile')
    #fullname = data.get('fullname')
    #address = data.get('address')
    #district_id = data.get('district_id')

    # Kiểm tra xem tài khoản, email hoặc số điện thoại đã tồn tại hay chưa
    query_check = f"SELECT Username, Email, Mobile FROM Customer WHERE Username = ? OR Email = ? OR Mobile = ?"
    cursor.execute(query_check, (username, email, mobile))
    existing_accounts = cursor.fetchall()
    error_messages = []

    for account in existing_accounts:
        if account.Username == username:
            error_messages.append('Tên tài khoản')
        if account.Email == email:
            error_messages.append('Email')
        if account.Mobile == mobile:
            error_messages.append('Số điện thoại')

    if error_messages:
        msg = ', '.join(error_messages)+' đã tồn tại.'
        print(msg)
        return jsonify({'message': msg}), 409

    # Thực thi truy vấn INSERT để thêm thông tin vào bảng Customer
    #query_insert = f"INSERT INTO Customer (Username, Password, Email, Mobile, FullName, Address, DistrictID) VALUES (?, ?, ?, ?, ?, ?, ?)"
    #cursor.execute(query_insert, (username, password, email, mobile, fullname, address, district_id))
    # query_insert = f"INSERT INTO Customer (CustomerID, Username, Password, Email, Mobile) VALUES (?, ?, ?, ?)"
    # cursor.execute(query_insert, (customerid, username, password, email, mobile))
    query_insert = f"INSERT INTO Customer (Username, Password, Email, Mobile) VALUES (?, ?, ?, ?)"
    cursor.execute(query_insert, (username, password, email, mobile))
    conn.commit()

    # Trả về phản hồi thành công
    msg = 'Thêm thông tin tài khoản thành công'
    print(msg)
    return jsonify({'message': msg}), 201

#---------------------------------------------------------------------------------------------------

@app.route('/api/account/data', methods=['POST'])
def get_tai_khoan():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    # Thực thi truy vấn SELECT để lấy dữ liệu từ bảng Customer
    query_select = "SELECT * FROM Customer"
    cursor.execute(query_select)
    rows = cursor.fetchall()

    # Tạo danh sách các bản ghi
    data = []
    for row in rows:
        record = {
            #'customer_id': row.CustomerID,
            'username': row.Username,
            'password': row.Password,
            #'id_quyen': row.ID_Quyen,
            'email': row.Email,
            'mobile': row.Mobile,
            #'fullname': row.FullName
        }
        data.append(record)

    # Trả về dữ liệu dưới dạng JSON
    print(data)
    return jsonify(data), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/account/login', methods=['POST'])
def check_account():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    fcm = data.get('fcm')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    password = data.get('password')

    # Kiểm tra nếu "ten_tai_khoan_email_sdt" có chứa ký tự "@"
    if "@" in ten_tai_khoan_email_sdt:
        # Kiểm tra trong cột "Email" và "Password"
        print("Đã đăng nhập bằng Email: ", ten_tai_khoan_email_sdt)
        query_check = "SELECT COUNT(*) FROM Customer WHERE Email = ? AND Password = ?"
        cursor.execute(query_check, (ten_tai_khoan_email_sdt, password))
        result = cursor.fetchone()

    # Kiểm tra nếu "ten_tai_khoan_email_sdt" toàn là số
    elif ten_tai_khoan_email_sdt.isdigit():
        # Kiểm tra trong cột "Mobile" và "Password"
        print("Đã đăng nhập bằng SDT: ", ten_tai_khoan_email_sdt)
        query_check = "SELECT COUNT(*) FROM Customer WHERE Mobile = ? AND Password = ?"
        cursor.execute(query_check, (ten_tai_khoan_email_sdt, password))
        result = cursor.fetchone()

    else:
        # Kiểm tra trong cột "Username" và "Password"
        print("Đã đăng nhập bằng Username: ", ten_tai_khoan_email_sdt)
        query_check = "SELECT COUNT(*) FROM Customer WHERE Username = ? AND Password = ?"
        cursor.execute(query_check, (ten_tai_khoan_email_sdt, password))
        result = cursor.fetchone()

    if result[0] > 0:
        print('Tồn tại')
        #------------------------------------ Post FCM ------------------------------------
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
        results = cursor.fetchall()
        customerid = results[0][0]
        try:
            cursor.execute("UPDATE Customer SET FCM = ? WHERE CustomerID = ?", fcm, customerid)
            print(f"Đã update FCM cho User {ten_tai_khoan_email_sdt}")
            conn.commit()
        except:
            msg = f"Lỗi! Không update được FCM cho User {ten_tai_khoan_email_sdt}"
            print(msg)
            return jsonify({'message': msg}), 500
        #-----------------------------------------------------------------------------------
        return jsonify({'Exist': 1}), 200
    else:
        print('Không tồn tại')
        return jsonify({'Exist': 0}), 404
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/account/lay-maxacnhan', methods=['POST'])
def lay_maxacnhan():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    email = data.get('email')

    # Câu truy vấn SELECT để tìm hàng chứa email trùng khớp
    select_query = f"SELECT * FROM Customer WHERE Email = ?"
    cursor.execute(select_query, email)
    rows = cursor.fetchall()

    # Nếu có hàng trùng khớp, tạo và gửi mã xác nhận
    if rows:
        verification_code = str(random.randint(1, 999999)).zfill(6)
        
        # Kiểm tra xem mã xác nhận đã tồn tại trong cột VerificationCode hay chưa
        while True:
            select_code_query = f"SELECT * FROM Customer WHERE VerificationCode = ?"
            cursor.execute(select_code_query, verification_code)
            rows_code = cursor.fetchall()
            if not rows_code:
                break
            verification_code = str(random.randint(1, 999999)).zfill(6)

        update_query = f"UPDATE Customer SET VerificationCode = ? WHERE Email = ?"
        cursor.execute(update_query, (verification_code, email))
        conn.commit()
        print('Mã xác nhận: ', verification_code)
        return jsonify({'message': verification_code}), 200
    else:
        msg = 'Không tìm thấy email trong cơ sở dữ liệu.'
        print(msg)
        return jsonify({'message': msg}), 404


#---------------------------------------------------------------------------------------------------

@app.route('/api/account/kt-maxacnhan', methods=['POST'])
def kt_maxacnhan():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    email = data.get('email')
    maxacnhan = data.get('maxacnhan')

    # Câu truy vấn SELECT để tìm hàng chứa mã xác nhận trùng khớp
    select_query = f"SELECT * FROM Customer WHERE VerificationCode = ? AND Email = ?"
    cursor.execute(select_query, (maxacnhan, email))

    # Nếu có hàng trùng khớp, cập nhật cột VerificationCode
    if cursor.fetchall():
        msg = 'Mã xác nhận Đúng'
        print(msg)
        return jsonify({'message': msg}), 200
    else:
        msg = 'Mã xác nhận Sai'
        print(msg)
        return jsonify({'message': msg}), 404
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/account/capnhat-matkhau', methods=['POST'])
def capnhat_matkhau():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    email = data.get('email')
    new_pw = data.get('matkhaumoi')

    # Câu truy vấn SELECT để tìm hàng chứa email trùng khớp và kiểm tra mật khẩu
    select_query = f"SELECT * FROM Customer WHERE Email = ?"
    cursor.execute(select_query, (email))
    rows = cursor.fetchall()

    if rows:
        current_pw = rows[0].Password  # Giả sử cột Password được lấy là current_pw

        # Kiểm tra new_pw có trùng với current_pw hay không
        if new_pw == current_pw:
            msg = 'Vừa nhập mật khẩu cũ'
            print(msg)
            return jsonify({'message': msg}), 400

        # Cập nhật mật khẩu mới
        update_query = f"UPDATE Customer SET Password = ? WHERE Email = ?"
        cursor.execute(update_query, (new_pw, email))
        conn.commit()
        msg = 'Cập nhật mật khẩu thành công'
        print(msg)
        return jsonify({'message': msg}), 200
    else:
        msg = 'Không tìm thấy email trong cơ sở dữ liệu.'
        print(msg)
        return jsonify({'message': msg}), 404

#---------------------------------------------------------------------------------------------------

@app.route('/api/account/post-fcm', methods=['POST'])
def post_fcm():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    fcm = data.get('fcm')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    
    print("fcm:", fcm, ' - ', type(fcm))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    # Từ Username lấy CustomerID trong bảng Customer
    if "@" in ten_tai_khoan_email_sdt:
        cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
    elif ten_tai_khoan_email_sdt.isdigit():
        cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
    else:
        cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
    results = cursor.fetchall()
    customerid = results[0][0]
    try:
        cursor.execute("UPDATE Customer SET FCM = ? WHERE CustomerID = ?", fcm, customerid)
        conn.commit()
        msg = f"Đã update FCM cho User {ten_tai_khoan_email_sdt}"
        print(msg)
        return jsonify({'message': msg}), 200
    except:
        msg = f"Lỗi! Không update được FCM cho User {ten_tai_khoan_email_sdt}"
        print(msg)
        return jsonify({'message': msg}), 500
            
####################################################################################################
@app.route('/api/ads/banner-img', methods=['GET'])
def banner():

    global random_banner
    global current_banner
    banner_files = os.listdir(banner_folder_path)
    # Chọn ngẫu nhiên một tệp tin ảnh từ thư mục banner
    while random_banner==current_banner:
        random_banner = random.choice(banner_files)
    current_banner = random_banner

    # Đường dẫn đầy đủ tới tệp tin ảnh
    image_path = os.path.join(banner_folder_path, random_banner)

    # Đọc nội dung tệp tin ảnh
    # with open(image_path, "rb") as image_file:
    #     image_data = image_file.read()
    
    img = cv2.imread(image_path)
    _, image_data = cv2.imencode('.jpg', img)
    
    # Chuyển đổi dữ liệu ảnh thành chuỗi base64
    base64_image = base64.b64encode(image_data).decode("utf-8")

    # Trả về chuỗi base64 cho app
    print("Vừa trả về chuỗi base64")
    return Response(base64_image, mimetype='text/plain')

####################################################################################################
@app.route('/api/lock/get-accesstoken', methods=['POST'])
def get_accesstoken(client_id='87ed6cf1e9274e65af6500193fd7dce8', 
                    clientsecret='5e56225a865fc7368f7e1e57b5bdd0fc', 
                    username='trinhnhattuyen12a4@gmail.com', 
                    password='nhattuyen0414'):
# def get_accesstoken(client_id='2ce5129232f74cc2ac89e24cdd04ec65', 
#                     clientsecret='5fc0bb10aa78a6fa48c0ff4b95e3c791', 
#                     username='datlongan@gmail.com', 
#                     password='Dat12345678'):
    print("Get access token ...")
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    url = "https://euapi.sciener.com/oauth2/token"
    
    data = {
        "clientId": client_id,
        "clientSecret": clientsecret,
        "username": username,
        "password": hashlib.md5(password.encode()).hexdigest()
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        print(response.json())
        return Response(response.json()['access_token'], mimetype='text/plain')
    else:
        print("Failed to get access token")
        return Response("Failed to get access token", mimetype='text/plain')
    
#---------------------------------------------------------------------------------------------------
    
@app.route('/api/lock/state', methods=['POST'])
def get_lockstate():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    client_id = data.get('client_id')
    lock_id = data.get('lock_id')
    access_token = data.get('access_token')
    now = datetime.datetime.now()
    new_time = now + datetime.timedelta(seconds=2)
    date = int(new_time.timestamp() * 1000)
    api_url = f"https://euapi.sciener.com/v3/lock/queryOpenState?clientId={client_id}&accessToken={access_token}&lockId={lock_id}&date={date}"

    try:
        response = requests.get(api_url)
        data = response.json()
        state = data.get('state')
        print('State: ', state)
        if state==0:
            return Response("Locked", mimetype='text/plain')
        elif state==1:
            return Response("Unlocked", mimetype='text/plain')
        else:
            return Response("Unknown", mimetype='text/plain')
        
    except requests.exceptions.RequestException as e:
        return Response("Error when get lock state", mimetype='text/plain')

#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/unlock', methods=['POST'])
def remote_lock():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    lock_id = data.get('lock_id')
    client_id = data.get('client_id')
    lock = data.get('lock')
    access_token = data.get('access_token')
    url = "https://euapi.sciener.com/v3/lock/unlock"
    if lock:
        url = "https://euapi.sciener.com/v3/lock/lock"
    
    now = datetime.datetime.now()
    new_time = now + datetime.timedelta(seconds=2)
    timestamp = int(new_time.timestamp() * 1000)
    
    data = {
        "clientId": client_id,
        "accessToken": access_token,
        "lockId": lock_id,
        "date": timestamp
    }
    response = requests.post(url, data=data)
    msg = response.json()
    if msg.get('errcode') == 0:
        if lock:
            msg = 'Lock Successful!'
            print(msg)
            return jsonify({'message': msg}), 200 
        else:
            msg = 'Unlock Successful!'
            print(msg)
            return jsonify({'message': msg}), 200
    else:
        if lock:
            msg = 'Lock Fail! ' + msg.get('errmsg')
            print(msg)
            return jsonify({'message': msg}), 404
        else:
            msg = 'Unlock Fail! '+msg.get('errmsg')
            print(msg)
            return jsonify({'message': msg}), 404

####################################################################################################

@app.route('/api/lock/homeinfo', methods=['POST'])
def homeinfo():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('username')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    home_info_list = []
    
    # Lấy CustomerID
    try:
        # Từ Username lấy CustomerID trong bảng Customer
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        results = cursor.fetchall()
        customerid = results[0][0]
    except:
        msg = f"Lỗi! Không lấy được CustomerID của User {ten_tai_khoan_email_sdt}"
        print(msg)
        return jsonify({'message': msg}), 404
    
    #---------------------------------------------------------------------------------------
    # LẤY NHÀ CỦA USER
    try:
        cursor.execute("SELECT HomeName, HomeAddress, DistrictID, HomeID FROM CustomerHome WHERE CustomerID = ?", customerid)
        results = cursor.fetchall()
        # Chuyển danh sách các tuple thành danh sách các dictionary
        
        for result in results:
            home_info_list.append({
                'HomeName': result[0],
                'HomeAddress': '',
                'DistrictID': result[2],
                'HomeID': result[3]
            })
        
        if len(results)==0:
            print(f"User {ten_tai_khoan_email_sdt} chưa thêm căn hộ nào")
        else:
            print(f"Có {len(results)} căn hộ của User {ten_tai_khoan_email_sdt}")
            
    except:
        msg = f"Lỗi! Không lấy được thông tin các căn hộ của User {ten_tai_khoan_email_sdt}"
        print(msg)
        return jsonify({'message': msg}), 404
    
    #---------------------------------------------------------------------------------------
    # LẤY NHÀ CỦA USER ĐƯỢC THÊM
    try:
        cursor.execute("SELECT HomeID, AdminID FROM HomeMember WHERE HomeMemberID = ?", customerid)
        results = cursor.fetchall()
        # Lấy thông tin căn hộ được thêm quyền
        for homeid, admin_id in results:
            cursor.execute("SELECT HomeName, HomeAddress, DistrictID FROM CustomerHome WHERE HomeID = ? AND CustomerID = ?", 
                        (homeid, admin_id))
            results_ = cursor.fetchone()
            # Chuyển danh sách các tuple thành danh sách các dictionary
            home_info_list.append({
                'HomeName': results_[0],
                'HomeAddress': results_[1],
                'DistrictID': results_[2],
                'HomeID': homeid
            })
        if len(results)==0:
            print(f"Không có căn hộ nào User {ten_tai_khoan_email_sdt} được thêm quyền")
        else:
            print(f"Có {len(results)} căn hộ User {ten_tai_khoan_email_sdt} được thêm quyền")
    except:
        msg = f"Lỗi! Không lấy được thông tin các căn hộ User {ten_tai_khoan_email_sdt} được thêm vào"
        print(msg)
        return jsonify({'message': msg}), 404
    
    # Chuyển danh sách thành định dạng JSON và trả về
    print(f"Trả về list thông tin các căn hộ của User {ten_tai_khoan_email_sdt}...")
    return json.dumps(home_info_list), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/delete-home', methods=['POST'])
def delete_home():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    homeid = data.get('homeid')
    print("homeid:", homeid, ' - ', type(homeid))

    # Camera
    try:
        cursor.execute("DELETE FROM Camera WHERE HomeID = ?", homeid)
        # print()
    except Exception as e:
        conn.rollback()
        msg = f"Không xóa được ở bảng Camera"
        print(msg)
        return jsonify({'message': msg}), 500
    #-----------------------------------------------------------------
    # Lock
    try:
        cursor.execute("DELETE FROM Lock WHERE HomeID = ?", homeid)
        # print()
    except Exception as e:
        conn.rollback()
        msg = f"Không xóa được ở bảng Lock"
        print(msg)
        return jsonify({'message': msg}), 500
    #-----------------------------------------------------------------    
    # Gateway
    try:
        cursor.execute("DELETE FROM Gateway WHERE HomeID = ?", homeid)
        # print()
    except Exception as e:
        conn.rollback()
        msg = f"Không xóa được ở bảng Gateway"
        print(msg)
        return jsonify({'message': msg}), 500
    #-----------------------------------------------------------------
    # HomeMember
    try:
        cursor.execute("DELETE FROM HomeMember WHERE HomeID = ?", homeid)
        # print()
    except Exception as e:
        conn.rollback()
        msg = f"Không xóa được ở bảng HomeMember"
        print(msg)
        return jsonify({'message': msg}), 500
    #-----------------------------------------------------------------
    # CustomerHome
    try:
        cursor.execute("DELETE FROM CustomerHome WHERE HomeID = ?", homeid)
        conn.commit()
        msg = f"Xóa thành công Home {homeid}"
        print(msg)
        return jsonify({'message': msg}), 200
    except Exception as e:
        conn.rollback()
        msg = f"Không xóa được ở bảng CustomerHome"
        print(msg)
        return jsonify({'message': msg}), 500
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/addhome', methods=['POST'])
def addhome():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    try:
        ten_tai_khoan_email_sdt = data.get('username')
        homename = data.get('homename')
        homeaddress = data.get('homeaddress')
        districtid = data.get('districtid')
        
        print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
        print("homename:", homename, ' - ', type(homename))
        print("homeaddress:", homeaddress, ' - ', type(homeaddress))
        print("districtid:", districtid, ' - ', type(districtid))
        
        # Từ Username lấy CustomerID trong bảng Customer
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        results = cursor.fetchall()
        customerid = results[0][0]
        print(customerid)
        # Kiểm tra nếu HomeName đã tồn tại
        cursor.execute("SELECT * FROM CustomerHome WHERE CustomerID = ? AND HomeName = ?", (customerid, homename))
        if cursor.fetchall():
            msg = 'Thêm nhà không thành công. Trùng HomeName!!!'
            print(msg)
            return jsonify({'message': msg}), 500
        
         
        cursor.execute("INSERT INTO CustomerHome (CustomerID, HomeName, HomeAddress, DistrictID) VALUES (?, ?, ?, ?)", 
                       (customerid, homename, homeaddress, districtid))
        conn.commit()
        msg = 'Thêm nhà thành công'
        print(msg)
        return jsonify({'message': msg}), 201
    
    except:
        msg = 'Thêm nhà không thành công'
        print(msg)
        return jsonify({'message': msg}), 500

####################################################################################################

@app.route('/api/lock/lockinfo', methods=['POST'])
def lockinfo():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('username')
    # homename = data.get('homename')
    homeid = data.get('homeid')

    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    # print("homename:", homename, ' - ', type(homename))
    print("homeid:", homeid, ' - ', type(homeid))
    #-------------------------------------------------
    # Lấy CustomerID
    try:
        # Từ Username lấy CustomerID trong bảng Customer
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        results = cursor.fetchall()
        customerid = results[0][0]
    except:
        msg = f"Lỗi! Không lấy được CustomerID của User {ten_tai_khoan_email_sdt}"
        print(msg)
        return jsonify({'message': msg}), 404
    
    try:
        # Lấy thông tin khóa của User
        cursor.execute("SELECT LockID, LockName, LockStatus FROM Lock WHERE HomeID = ?", homeid)
        results = cursor.fetchall()
        # Chuyển danh sách các tuple thành danh sách các dictionary
        lock_info_list = []
        for result in results:
            lock_info_list.append({
                'LockID': result[0],
                'LockName': result[1],
                'LockStatus': result[2] if result[2]!=None else 'Unknown',
            })

        # Chuyển danh sách thành định dạng JSON và trả về
        print(f"Có {len(results)} khóa của căn hộ")
        return json.dumps(lock_info_list), 200
    except:
        try:
            # Lấy thông tin khóa của người khác mà User được thêm
            cursor.execute("SELECT AdminID FROM HomeMember WHERE HomeMemberID = ? AND HomeID = ?", (customerid, homeid))
            if cursor.fetchall():
                print(f"Đây là căn hộ được phân quyền bởi User {cursor.fetchall()[0][0]}")
                        
                # Lấy thông tin khóa
                cursor.execute("SELECT LockID, LockName, LockStatus FROM Lock WHERE HomeID = ?", homeid)
                results = cursor.fetchall()
                # Chuyển danh sách các tuple thành danh sách các dictionary
                lock_info_list = []
                for result in results:
                    lock_info_list.append({
                        'LockID': result[0],
                        'LockName': result[1],
                        'LockStatus': result[2] if result[2]!=None else 'Unknown',
                    })

                # Chuyển danh sách thành định dạng JSON và trả về
                print(f"Có {len(results)} khóa của căn hộ")
                return json.dumps(lock_info_list), 200
        except:
            msg = "Lỗi! Không lấy được thông tin các khóa"
            print(msg)
            return jsonify({'message': msg}), 404

#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/delete-lock', methods=['POST'])
def delete_lock():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    lockid = data.get('lockid')
    print("lockid:", lockid, ' - ', type(lockid))
    
    # Xóa khóa (LockHistory)
    try:
        cursor.execute("DELETE FROM LockHistory WHERE LockID = ?", lockid)
        msg = f"Xóa thành công khóa {lockid} trong bảng LockHistory"
        print(msg)
    except Exception as e:
        conn.rollback()
        msg = f"Không xóa được khóa {lockid} trong bảng LockHistory"
        print(msg)
        return jsonify({'message': msg}), 500
    
    # Xóa khóa (Lock)
    try:
        cursor.execute("DELETE FROM Lock WHERE LockID = ?", lockid)
        conn.commit()
        msg = f"Xóa thành công khóa {lockid} trong bảng Lock"
        print(msg)
        return jsonify({'message': msg}), 200
    except Exception as e:
        conn.rollback()
        msg = f"Không xóa được khóa {lockid} trong bảng Lock"
        print(msg)
        return jsonify({'message': msg}), 500
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/addlock', methods=['POST'])
def addlock():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    lockid = data.get('lockid')
    lockname = data.get('lockname')
    ten_tai_khoan_email_sdt = data.get('username')
    homename = data.get('homename')

    print("lockid:", lockid, ' - ', type(lockid))
    print("lockname:", lockname, ' - ', type(lockname))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("homename:", homename, ' - ', type(homename))
    
    #-------------------------------------------------
    try:    
        # Từ Username lấy CustomerID trong bảng Customer
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        results = cursor.fetchall()
        customer_id = results[0][0]
        
        # Từ CustomerID lấy HomeID trong bảng CustomerHome
        cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ? AND HomeName = ?", (customer_id, homename))
        results = cursor.fetchall()
        homeid = results[0][0]
    except:
        msg = 'Không lấy được HomeID từ UserName'
        print(msg)
        return jsonify({'message': msg}), 500
    
    #-------------------------------------------------
    
    # Kiểm tra nếu LockName đã tồn tại
    cursor.execute("SELECT * FROM Lock WHERE LockName = ? AND HomeID = ?", (lockname, homeid))
    if cursor.fetchall():
        msg = 'Thêm khóa không thành công. Trùng LockName!!!'
        print(msg)
        return jsonify({'message': msg}), 500
    
    #-------------------------------------------------
    
    try:
        cursor.execute("INSERT INTO Lock (LockID, LockName, HomeID) VALUES (?, ?, ?)", (lockid, lockname, homeid))
        conn.commit()
        msg = 'Thêm khóa thành công'
        print(msg)
        return jsonify({'message': msg}), 201
    except:
        msg = 'Thêm khóa không thành công'
        print(msg)
        return jsonify({'message': msg}), 500
    
####################################################################################################

@app.route('/api/lock/add-home-member', methods=['POST'])
def add_home_member():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    homemember = data.get('homemember')
    ten_tai_khoan_email_sdt = data.get('username')
    homename = data.get('homename')
    
    print("homemember:", homemember, ' - ', type(homemember))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("homename:", homename, ' - ', type(homename))
    
    #---------------------------------------------------------------------------------------
    try:
        # Từ "ten_tai_khoan_email_sdt" lấy CustomerID của admin trong bảng Customer
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
        results = cursor.fetchall()
        admin_id = results[0][0]
    except:
        msg = f"Lỗi! Không lấy được CustomerID của Admin {ten_tai_khoan_email_sdt}"
        print(msg)
        return jsonify({'message': msg}), 404
    #---------------------------------------------------------------------------------------
    try:
        # Từ "homename" lấy HomeID của admin trong bảng CustomerHome
        cursor.execute("SELECT HomeID FROM CustomerHome WHERE HomeName = ? AND CustomerID = ?", (homename, admin_id))
        results = cursor.fetchall()
        homeid = results[0][0]
    except:
        msg = f"Lỗi! Không lấy được HomeID của Admin {ten_tai_khoan_email_sdt}"
        print(msg)
        return jsonify({'message': msg}), 404
    #---------------------------------------------------------------------------------------
    try:
        # Từ "homemember" lấy CustomerID của HomeMember trong bảng Customer
        if "@" in homemember:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", homemember)
        elif homemember.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", homemember)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", homemember)
        results = cursor.fetchall()
        homemember_id = results[0][0]
    except:
        msg = f"Lỗi! Không lấy được CustomerID của HomeMember {homemember}"
        print(msg)
        return jsonify({'message': msg}), 404
    #---------------------------------------------------------------------------------------
    # Kiểm tra thêm quyền home-user này chưa
    cursor.execute("SELECT * FROM HomeMember WHERE HomeID = ? AND HomeMemberID = ?", (homeid, homemember_id))
    if cursor.fetchall():
        msg = f"Không thêm được. Trước đó đã thêm User {homemember} vào căn {homename}!"
        print(msg)
        return jsonify({'message': msg}), 404
    #---------------------------------------------------------------------------------------
    try:
        cursor.execute("INSERT INTO HomeMember (AdminID, HomeID, HomeMemberID) VALUES (?, ?, ?)",
                       (admin_id, homeid, homemember_id))
        conn.commit()
        msg = f"Đã thêm User {homemember} và căn hộ {homename} của User {ten_tai_khoan_email_sdt}"
        print(msg)
        return jsonify({'message': msg}), 201
    except:
        msg = f"Lỗi! Không thêm HomeMember được!"
        print(msg)
        return jsonify({'message': msg}), 404
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/delete-home-member', methods=['POST'])
def delete_home_member():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    homeid = data.get('homeid')
    ten_tai_khoan_email_sdt_member = data.get('username')
    
    print("homeid:", homeid, ' - ', type(homeid))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt_member, ' - ', type(ten_tai_khoan_email_sdt_member))
    
    #---------------------------------------------------------------------------------------
    try:
        # Từ "ten_tai_khoan_email_sdt_member" lấy CustomerID của member trong bảng Customer
        if "@" in ten_tai_khoan_email_sdt_member:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt_member)
        elif ten_tai_khoan_email_sdt_member.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt_member)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt_member)
        results = cursor.fetchall()
        member_id = results[0][0]
    except:
        msg = f"Lỗi! Không lấy được CustomerID của Member {ten_tai_khoan_email_sdt_member}"
        print(msg)
        return jsonify({'message': msg}), 404
    #---------------------------------------------------------------------------------------
    try:
        # Xóa quyền
        cursor.execute("DELETE FROM HomeMember WHERE HomeMemberID = ? AND HomeID = ?", (member_id, homeid))
        conn.commit()
        msg = f"Đã xóa User {ten_tai_khoan_email_sdt_member} khỏi căn hộ {homeid}"
        print(msg)
        return jsonify({'message': msg}), 200
    except:
        msg = f"Lỗi! Không xóa được User {ten_tai_khoan_email_sdt_member} khỏi căn hộ {homeid}"
        print(msg)
        return jsonify({'message': msg}), 404
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/home-member-list', methods=['POST'])
def homememberlist():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    homeid = data.get('homeid')
    ten_tai_khoan_email_sdt = data.get('username')
    
    print("homeid:", homeid, ' - ', type(homeid))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))

    try:
        # Từ "ten_tai_khoan_email_sdt" lấy CustomerID của admin trong bảng Customer
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
        results = cursor.fetchall()
        admin_id = results[0][0]
    except:
        msg = f"Lỗi! Không lấy được CustomerID của Admin {ten_tai_khoan_email_sdt}"
        print(msg)
        return jsonify({'message': msg}), 404
    #---------------------------------------------------------------------------------------
    try:
        member_list = []
        # Từ "homename" lấy HomeID của admin trong bảng CustomerHome
        cursor.execute("SELECT HomeMemberID FROM HomeMember WHERE AdminID = ? AND HomeID = ?", (admin_id, homeid))
        members = cursor.fetchall()
        for member_id in members:
            cursor.execute("SELECT Username, Email, Mobile, FullName FROM Customer WHERE CustomerID = ?", member_id[0])
            result = cursor.fetchone()
            member_list.append({
                'Username': result[0],
                'Email': result[1],
                'Mobile': result[2],
                'FullName': result[3]
            })
        print(f"Trả về list các User được thêm quyền của căn hộ {homeid}...")
        return json.dumps(member_list), 200
    except:
        msg = f"Lỗi! Không lấy được list các User được thêm quyền của căn hộ {homeid}"
        print(msg)
        return jsonify({'message': msg}), 404
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/updatehistory', methods=['POST'])
def update_history():
    # Lấy thông tin từ yêu cầu POST
    data = request.get_json()
    
    # Kiểm tra Key
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400

    # Lấy dữ liệu từ request
    lock_id = data.get('lock_id')
    history_description = data.get('history_description')
    history_code = data.get('history_code')
    history_date_str = data.get('history_date') # String -> "2023-07-21 15:30:00"

    # Chuyển đổi định dạng datetime
    try:
        history_date = datetime.strptime(history_date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        msg = "Invalid HistoryDate format. It should be in format 'YYYY-MM-DD HH:MM:SS'"
        print(msg)
        return jsonify({"error": msg}), 400

    # Thêm dữ liệu vào bảng 'LockHistory' trong CSDL
    cursor.execute("INSERT INTO LockHistory (LockID, HistoryDescription, HistoryCode, HistoryDate) VALUES (?, ?, ?, ?)", 
                   (lock_id, history_description, history_code, history_date))
    conn.commit()

    return jsonify({"message": "LockHistory updated successfully"}), 201

#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/get-history', methods=['POST'])
def get_history():
    # Lấy thông tin từ yêu cầu POST
    data = request.get_json()
    
    # Kiểm tra Key
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400

    lock_id = data.get('lock_id')
    history_list = []
    try:
        cursor.execute("SELECT HistoryDescription, HistoryCode, HistoryDate FROM LockHistory WHERE LockID = ?", lock_id)
        history = cursor.fetchall()
        for i in history:
            history_list.append({
                'HistoryDescription': i[0],
                'HistoryCode': i[1],
                'HistoryDate': i[2].strftime("%Y-%m-%d %H:%M:%S"),
            })
        print(f"Trả về lịch sử khóa {lock_id}")
        return json.dumps(history_list), 200
    except Exception as e:
        print(e)

#---------------------------------------------------------------------------------------------------

# @app.route('/api/camera/add', methods=['POST'])
# def add_camera():
#     data = request.get_json()
#     key = data.get('key')
#     if key not in api_keys:
#         print('Sai key')
#         return jsonify({'message': 'Sai key'}), 400
    
#     homeid = data.get('homeid')
#     camera_name = data.get('camera_name')
#     cam_username = data.get('cam_username')
#     cam_pass = data.get('cam_pass')
#     rtsp = data.get('rtsp')
#     print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))


#---------------------------------------------------------------------------------------------------

@app.route('/api/camera/get-user-camera', methods=['POST'])
def get_camera():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('username')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    try:
        # Từ "ten_tai_khoan_email_sdt" lấy CustomerID của admin trong bảng Customer
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
        results = cursor.fetchall()
        customer_id = results[0][0]
    except:
        msg = f"Lỗi! Không lấy được CustomerID của user {ten_tai_khoan_email_sdt}"
        print(msg)
        return jsonify({'message': msg}), 404
    
    # Lấy danh sách camera của User
    camera_list = []
    try:
        cursor.execute(f"""SELECT lc.LockID, lc.CameraID
                            FROM Lock_Camera lc
                            JOIN CustomerHome ch ON lc.HomeID = ch.HomeID
                            WHERE ch.CustomerID = '{customer_id}'
                        """)
        results = cursor.fetchall()
        for i in results:
            # Nếu cam không có khóa
            if i.LockID==None:
                cursor.execute("SELECT * FROM Camera WHERE CameraID = ?", i.CameraID)
                cam = cursor.fetchone()
                #--------------------------------------------------------------------------
                cam_img = cam.CameraName
                cam_img_path = os.path.join(cam_img_folder_path, cam_img+'.jpg')
                img = cv2.imread(cam_img_path)
                _, image_data = cv2.imencode('.jpg', img)
                
                # Chuyển đổi dữ liệu ảnh thành chuỗi base64
                base64_image = base64.b64encode(image_data).decode("utf-8")
                #--------------------------------------------------------------------------    
                camera_list.append({
                    'LockID': None,
                    'LockName': None,
                    'CameraName': cam.CameraName,
                    'RTSP': cam.RTSP,
                    'Hinh': base64_image,
                })
            # Nếu cam có khóa
            else:
                cursor.execute("SELECT * FROM Lock WHERE LockID = ?", i.LockID)
                lock = cursor.fetchone()
                cursor.execute("SELECT * FROM Camera WHERE CameraID = ?", i.CameraID)
                cam = cursor.fetchone()
                #--------------------------------------------------------------------------
                cam_img = cam.CameraName
                cam_img_path = os.path.join(cam_img_folder_path, cam_img+'.jpg')
                img = cv2.imread(cam_img_path)
                _, image_data = cv2.imencode('.jpg', img)
                
                # Chuyển đổi dữ liệu ảnh thành chuỗi base64
                base64_image = base64.b64encode(image_data).decode("utf-8")
                #--------------------------------------------------------------------------             
                camera_list.append({
                    'LockID': lock.LockID,
                    'LockName': lock.LockName,
                    'CameraName': cam.CameraName,
                    'RTSP': cam.RTSP,
                    'Hinh': base64_image,
                })
                
        print(f"Trả về danh sách camera của user {ten_tai_khoan_email_sdt}")
        return json.dumps(camera_list), 200
    except Exception as e:
        msg = f"Lỗi! Không lấy được danh sách camera của user {ten_tai_khoan_email_sdt}"
        print(msg)
        print(e)

#---------------------------------------------------------------------------------------------------

@app.route('/api/camera/get-img-camera', methods=['POST'])
def get_img_camera():
    
    data = request.get_json()
    rtsp = data.get('rtsp')
    print("rtsp:", rtsp, ' - ', type(rtsp))
    
    # Đường dẫn đầy đủ tới tệp tin ảnh
    image_path = os.path.join(banner_folder_path, random_banner)

    # Đọc nội dung tệp tin ảnh
    # with open(image_path, "rb") as image_file:
    #     image_data = image_file.read()
    
    img = cv2.imread(image_path)
    _, image_data = cv2.imencode('.jpg', img)
    
    # Chuyển đổi dữ liệu ảnh thành chuỗi base64
    base64_image = base64.b64encode(image_data).decode("utf-8")

    # Trả về chuỗi base64 cho app
    print("Vừa trả về chuỗi base64")
    return Response(base64_image, mimetype='text/plain')
#---------------------------------------------------------------------------------------------------
@app.route('/api/lock/record', methods=['POST'])
def get_lockrecord():
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        return jsonify({'message': 'Sai key'}), 400
    client_id = data.get('client_id')
    lock_id = data.get('lock_id')
    access_token = data.get('access_token')
    now = datetime.datetime.now()
    new_time = now + datetime.timedelta(seconds=2)
    date = int(new_time.timestamp() * 1000)
    api_url = f"https://euapi.sciener.com/v3/lockRecord/list?clientId={client_id}&accessToken={access_token}&startDate=1526674054000&endDate={date}&lockId={lock_id}&pageNo=1&pagesize=50&date={date}"

    try:
        response = requests.get(api_url)
        data = response.json()
        print(data)
        return Response("OK", mimetype='text/plain')
        
    except requests.exceptions.RequestException as e:
        return Response("Error when get lock state", mimetype='text/plain')

####################################################################################################
####################################################################################################
if __name__ == '__main__':
    while True:
        try:
            app.run(host=ip_address, port=5000)
        except pyodbc.OperationalError:
            conn = connect_to_database()
            cursor = conn.cursor()
            pass
