
from flask import Flask, request, jsonify, Response
import socket, pyodbc, random, time, os, cv2, base64, hashlib, requests, datetime, json, math, hashlib, argon2
from argon2 import PasswordHasher
from matplotlib import pyplot
import numpy as np
import pandas as pd

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from base64 import b64encode, b64decode

app = Flask(__name__)
value = None
random_banner = ''
current_banner = ''
banner_folder_path = 'banner'
cam_img_folder_path = 'cam_img'
detectorssd = cv2.dnn.readNetFromCaffe("pre_model/deploy.prototxt","pre_model/res10_300x300_ssd_iter_140000.caffemodel")
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
            print()
            print("Kết nối Database thành công!")
            return conn  # Trả về kết nối nếu thành công
        except pyodbc.OperationalError:
            if retry_count < max_retries - 1:
                print("Kết nối không thành công. Thử kết nối lại sau {} giây.".format(retry_delay))
                time.sleep(retry_delay)
            else:
                print("Không thể kết nối đến cơ sở dữ liệu sau nhiều lần thử. Đã đạt đến giới hạn thử lại.")
                raise

def base64_to_array(anh_base64):
        try:
            img_arr = np.frombuffer(base64.b64decode(anh_base64), dtype=np.uint8)
            img_arr = cv2.imdecode(img_arr, cv2.IMREAD_ANYCOLOR)
        except:
            return "Không chuyển được ảnh base64 sang array"
        return img_arr


def padding_face(imgface,target_size=(224,224)):
    try:
        tile= target_size[0]/(imgface.shape[0]+1)
        he=math.floor(tile*imgface.shape[0])
        wi=math.floor(tile*imgface.shape[1])

        imgface=cv2.resize(imgface,(wi,he))
        target_size=(224, 224)
        factor_0 = target_size[0] / imgface.shape[0]
        factor_1 = target_size[1] / imgface.shape[1]
        factor = min(factor_0, factor_1)
        dsize = (int(imgface.shape[1] * factor), int(imgface.shape[0] * factor))
        imgface = cv2.resize(imgface, dsize)
        # Then pad the other side to the target size by adding black pixels
        diff_0 = target_size[0] - imgface.shape[0]
        diff_1 = target_size[1] - imgface.shape[1]
        # Put the base image in the middle of the padded image
        imgface = np.pad(imgface, ((diff_0 // 2, diff_0 - diff_0 // 2), (diff_1 // 2, diff_1 - diff_1 // 2), (0, 0)), 'constant')
        #double check: if target image is not still the same size with target.
        if imgface.shape[0:2] != target_size:
            imgface = cv2.resize(imgface, target_size)
        return imgface
    except:
        print("err padd")
        return imgface

def argon2_encode(input_password):
    """
    Hàm mã hóa mật khẩu sử dụng thuật toán Argon2.

    Parameters:
    - input_password: Mật khẩu cần mã hóa.

    Returns:
    - Chuỗi Argon2 hash.
    """
    ph = PasswordHasher()
    hashed_password = ph.hash(input_password)
    return hashed_password

def argon2_compare(input_password, hashed_password):
    """
    Hàm kiểm tra sự tương đồng giữa một mật khẩu và một chuỗi Argon2 hash.

    Parameters:
    - input_password: Mật khẩu cần kiểm tra.
    - hashed_password: Chuỗi Argon2 hash cần so sánh.

    Returns:
    - True nếu input_password và hashed_password tương đồng, False nếu không.
    """
    ph = PasswordHasher()
    try:
        ph.verify(hashed_password, input_password)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False

def aes_encrypt(encrypt_text, key=b'x?C^pz62}bDM&)<duM9]:/kWze/j13J4'):
    # Thêm padding vào dữ liệu để đảm bảo độ dài là bội số của 16 bytes
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(encrypt_text.encode()) + padder.finalize()

    # Mã hóa dữ liệu đã được padding
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return b64encode(ciphertext).decode()

def aes_decrypt(decrypt_text, key=b'x?C^pz62}bDM&)<duM9]:/kWze/j13J4'):
    # Giải mã dữ liệu
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(b64decode(decrypt_text)) + decryptor.finalize()

    # Bỏ padding
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_data) + unpadder.finalize()

    return plaintext.decode()

def save_thumbnail(rtsp_url, camera_id, thumbnail_path='cam_img'):
    # Mở kết nối RTSP
    cap = cv2.VideoCapture(rtsp_url)

    # Kiểm tra xem kết nối có thành công không
    if not cap.isOpened():
        print("Không thể kết nối đến luồng RTSP.")
        return

    # Bỏ qua 4 khung hình đầu tiên
    for _ in range(4):
        ret, _ = cap.read()
        if not ret:
            print("Không thể đọc khung hình từ luồng RTSP.")
            cap.release()
            return

    # Đọc khung hình thứ 5
    ret, frame = cap.read()

    # Kiểm tra xem có đọc được khung hình không
    if not ret:
        print("Không thể đọc khung hình từ luồng RTSP.")
        cap.release()
        return

    # Lưu khung hình thứ 5
    thumbnail_file_path = os.path.join(thumbnail_path, f"{camera_id}.jpg")
    cv2.imwrite(thumbnail_file_path, frame)

    print(f"Khung hình thứ 5 đã được lưu tại: {thumbnail_file_path}")

    # Giải phóng tài nguyên
    cap.release()
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

####################################################################################################

@app.route('/api/account/sign-up', methods=['POST'])
def them_tai_khoan():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    # customerid = data.get('customerid')
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    mobile = data.get('mobile')
    fullname = data.get('fullname')
    #address = data.get('address')
    #district_id = data.get('district_id')
    
    # Mã hóa mật khẩu
    password = argon2_encode(password)

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
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 409
    
    # Thực thi truy vấn INSERT để thêm thông tin vào bảng Customer
    query_insert = f"INSERT INTO Customer (Username, Password, Email, Mobile, FullName) VALUES (?, ?, ?, ?, ?)"
    cursor.execute(query_insert, (username, password, email, mobile, fullname))
    conn.commit()

    # Trả về phản hồi thành công
    msg = 'Thêm thông tin tài khoản thành công'
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 201

#---------------------------------------------------------------------------------------------------

@app.route('/api/account/data', methods=['POST'])
def get_tai_khoan():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
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
    cursor.close()
    conn.close()
    return jsonify(data), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/account/login', methods=['POST'])
def check_account():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    fcm = data.get('fcm')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    password = data.get('password')
    
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("password:", password, ' - ', type(password))
    
    # Mã hóa mật khẩu
    password = argon2_encode(password)
    
    # Kiểm tra nếu "ten_tai_khoan_email_sdt" có chứa ký tự "@"
    if "@" in ten_tai_khoan_email_sdt:
        # Kiểm tra có tồn tại Email này không
        cursor.execute("SELECT * FROM Customer WHERE Email = ?", (ten_tai_khoan_email_sdt,))
        result = cursor.fetchone()
        if not result:
            msg = "Email does not exist"
            print(msg)
            cursor.close()
            conn.close()
            return jsonify({'message': msg}), 404
        
        # Kiểm tra trong cột "Email" và "Password"
        print("Đăng nhập bằng Email: ", ten_tai_khoan_email_sdt)
        query_check = "SELECT * FROM Customer WHERE Email = ?"
        cursor.execute(query_check, (ten_tai_khoan_email_sdt))
        result = cursor.fetchone()
        if argon2_compare(password, result.Password):
            msg = "Wrong Password"
            print(msg)
            cursor.close()
            conn.close()
            return jsonify({'message': msg}), 404

    # Kiểm tra nếu "ten_tai_khoan_email_sdt" toàn là số
    elif ten_tai_khoan_email_sdt.isdigit():
        # Kiểm tra có tồn tại SDT này không
        cursor.execute("SELECT * FROM Customer WHERE Mobile = ?", (ten_tai_khoan_email_sdt,))
        result = cursor.fetchone()
        if not result:
            msg = "Phone number does not exist"
            print(msg)
            cursor.close()
            conn.close()
            return jsonify({'message': msg}), 404
        
        # Kiểm tra trong cột "Mobile" và "Password"
        print("Đăng nhập bằng SDT: ", ten_tai_khoan_email_sdt)
        query_check = "SELECT * FROM Customer WHERE Mobile = ?"
        cursor.execute(query_check, (ten_tai_khoan_email_sdt))
        result = cursor.fetchone()
        if argon2_compare(password, result.Password):
            msg = "Wrong Password"
            print(msg)
            cursor.close()
            conn.close()
            return jsonify({'message': msg}), 404

    else:
        # Kiểm tra có tồn tại Tên người dùng này không
        cursor.execute("SELECT * FROM Customer WHERE Username = ?", (ten_tai_khoan_email_sdt,))
        result = cursor.fetchone()
        if not result:
            msg = "Username does not exist"
            print(msg)
            cursor.close()
            conn.close()
            return jsonify({'message': msg}), 404
        
        # Kiểm tra trong cột "Username" và "Password"
        print("Đăng nhập bằng Username: ", ten_tai_khoan_email_sdt)
        query_check = "SELECT * FROM Customer WHERE Username = ?"
        cursor.execute(query_check, (ten_tai_khoan_email_sdt))
        result = cursor.fetchone()
        if argon2_compare(password, result.Password):
            msg = "Wrong Password"
            print(msg)
            cursor.close()
            conn.close()
            return jsonify({'message': msg}), 404

    #------------------------------------ Thêm FCM ------------------------------------
    if "@" in ten_tai_khoan_email_sdt:
        cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
    elif ten_tai_khoan_email_sdt.isdigit():
        cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
    else:
        cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
    results = cursor.fetchall()
    customerid = results[0][0]
    try:
        cursor.execute("SELECT 1 FROM CustomerDevice WHERE CustomerID = ? AND FCM = ?", (customerid, fcm))
        if cursor.fetchone():
            print("Cặp giá trị CustomerID và FCM đã tồn tại, k thực hiện thêm mới")
        else:
            current_datetime = datetime.datetime.now()
            cursor.execute("INSERT INTO CustomerDevice (CustomerID, FCM, LoginTime) VALUES (?, ?, ?)", (customerid, fcm, current_datetime))
            print(f"Đã thêm FCM cho User {ten_tai_khoan_email_sdt}")
            conn.commit()
    except:
        msg = f"Lỗi! Không thêm được FCM cho User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    #-----------------------------------------------------------------------------------
    msg = 'Login successfull!'
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/account/logout', methods=['POST'])
def logout():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    fcm = data.get('fcm')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')   

    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        # cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        # username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    cursor.execute("DELETE FROM CustomerDevice WHERE CustomerID = ? AND FCM = ?", (customerid, fcm))
    conn.commit()
    
    msg = f"Logout! {ten_tai_khoan_email_sdt}"
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 200
#---------------------------------------------------------------------------------------------------

@app.route('/api/account/lay-maxacnhan', methods=['POST'])
def lay_maxacnhan():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
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
        cursor.close()
        conn.close()
        return verification_code, 200
    else:
        msg = 'Không tìm thấy email trong cơ sở dữ liệu.'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404


#---------------------------------------------------------------------------------------------------

@app.route('/api/account/kt-maxacnhan', methods=['POST'])
def kt_maxacnhan():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
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
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 200
    else:
        msg = 'Mã xác nhận Sai'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/account/capnhat-matkhau', methods=['POST'])
def capnhat_matkhau():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
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
        if argon2_compare(new_pw, current_pw):
            msg = 'Vừa nhập mật khẩu cũ'
            print(msg)
            return jsonify({'message': msg}), 400

        # Cập nhật mật khẩu mới
        update_query = f"UPDATE Customer SET Password = ? WHERE Email = ?"
        cursor.execute(update_query, (argon2_encode(new_pw), email))
        conn.commit()
        msg = 'Cập nhật mật khẩu thành công'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 200
    else:
        msg = 'Không tìm thấy email trong cơ sở dữ liệu.'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404

#---------------------------------------------------------------------------------------------------

@app.route('/api/account/set-avatar', methods=['POST'])
def set_avatar():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    avatar_base64 = data.get('avatar_base64')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        # cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        # username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    cursor.execute("UPDATE Customer SET Avatar = ? WHERE CustomerID = ?", (avatar_base64, customerid))
    conn.commit()
    msg = f'Đã set avatar cho User {ten_tai_khoan_email_sdt}'
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/account/get-avatar', methods=['POST'])
def get_avatar():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    # avatar_base64 = data.get('avatar_base64')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        # cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        # username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    cursor.execute("SELECT Avatar FROM Customer WHERE CustomerID = ?", (customerid,))
    avatar_base64 = cursor.fetchone().Avatar
    print("Vừa trả về chuỗi base64 của avatar")
    cursor.close()
    conn.close()
    return Response(avatar_base64, mimetype='text/plain')

#---------------------------------------------------------------------------------------------------

@app.route('/api/account/delete', methods=['POST'])
def delete_account():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    # avatar_base64 = data.get('avatar_base64')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    print(username, ' - ', customerid)
    cursor.execute("DELETE FROM Customer WHERE CustomerID = ?", (customerid,))
    conn.commit()
    msg = "Account deleted"
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 201      
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

@app.route('/api/home/homeinfo', methods=['POST'])
def homeinfo():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    home_info_list = []
    
    # Lấy CustomerID
    try:
        # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
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
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    #---------------------------------------------------------------------------------------
    # LẤY NHÀ CỦA USER
    try:
        cursor.execute("SELECT HomeName, HomeAddress, DistrictID, HomeID FROM CustomerHome WHERE CustomerID = ?", customerid)
        results = cursor.fetchall()
        # Chuyển danh sách các tuple thành danh sách các dictionary
        
        for result in results:
            # Lấy các cam trong nhà đó
            cursor.execute("SELECT CameraName, CameraID FROM Camera WHERE HomeID = ?", result.HomeID)
            cam = cursor.fetchall()
            home_info_list.append({
                'HomeName': result.HomeName,
                'HomeAddress': result.HomeAddress,
                'DistrictID': result.DistrictID,
                'HomeID': result.HomeID,
                'Owner': '1',
                'CameraID': [i.CameraID for i in cam],
                'CameraName': [i.CameraName for i in cam],
            })
        
        if len(results)==0:
            print(f"User {ten_tai_khoan_email_sdt} chưa thêm căn hộ nào")
        else:
            print(f"Có {len(results)} căn hộ của User {ten_tai_khoan_email_sdt}")
        
    except:
        msg = f"Lỗi! Không lấy được thông tin các căn hộ của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    #---------------------------------------------------------------------------------------
    # LẤY NHÀ CỦA USER ĐƯỢC THÊM
    # try:
    cursor.execute("SELECT HomeID, AdminID FROM HomeMember WHERE HomeMemberID = ?", customerid)
    results = cursor.fetchall()
    # Lấy thông tin căn hộ được thêm quyền
    for homeid, admin_id in results:
        cursor.execute("SELECT HomeName, HomeAddress, DistrictID FROM CustomerHome WHERE HomeID = ? AND CustomerID = ?", 
                    (homeid, admin_id))
        result = cursor.fetchone()
        # Lấy các cam trong nhà đó
        cursor.execute("SELECT CameraName, CameraID FROM Camera WHERE HomeID = ?", homeid)
        cam = cursor.fetchall()
        # Chuyển danh sách các tuple thành danh sách các dictionary
        home_info_list.append({
            'HomeName': result.HomeName,
            'HomeAddress': result.HomeAddress,
            'DistrictID': result.DistrictID,
            'HomeID': homeid,
            'Owner': '0',
            'CameraID': [i.CameraID for i in cam],
            'CameraName': [i.CameraName for i in cam],
        })
    if len(results)==0:
        print(f"Không có căn hộ nào User {ten_tai_khoan_email_sdt} được thêm quyền")
    else:
        print(f"Có {len(results)} căn hộ User {ten_tai_khoan_email_sdt} được thêm quyền")
    # except:
    #     msg = f"Lỗi! Không lấy được thông tin các căn hộ User {ten_tai_khoan_email_sdt} được thêm vào"
    #     print(msg)
    #     cursor.close()
    #     conn.close()
    #     return jsonify({'message': msg}), 404
    
    # Chuyển danh sách thành định dạng JSON và trả về
    cursor.close()
    conn.close()
    print(f"Trả về list thông tin các căn hộ của User {ten_tai_khoan_email_sdt}...")
    return json.dumps(home_info_list), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/home/delete-home', methods=['POST'])
def delete_home():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
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
        cursor.close()
        conn.close()
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
        cursor.close()
        conn.close()
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
        cursor.close()
        conn.close()
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
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    #-----------------------------------------------------------------
    # CustomerHome
    try:
        cursor.execute("DELETE FROM CustomerHome WHERE HomeID = ?", homeid)
        conn.commit()
        msg = f"Xóa thành công Home {homeid}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 200
    except Exception as e:
        conn.rollback()
        msg = f"Không xóa được ở bảng CustomerHome"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/home/addhome', methods=['POST'])
def addhome():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    try:
        ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
        homename = data.get('homename')
        homeaddress = data.get('homeaddress')
        districtid = data.get('districtid')
        
        print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
        print("homename:", homename, ' - ', type(homename))
        print("homeaddress:", homeaddress, ' - ', type(homeaddress))
        print("districtid:", districtid, ' - ', type(districtid))
        
        # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
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
            msg = 'Tên nhà đã tồn tại'
            print(msg)
            cursor.close()
            conn.close()
            return jsonify({'message': msg}), 500
        
         
        cursor.execute("INSERT INTO CustomerHome (CustomerID, HomeName, HomeAddress, DistrictID) VALUES (?, ?, ?, ?)", 
                       (customerid, homename, homeaddress, districtid))
        conn.commit()
        msg = 'Thêm nhà thành công'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 201
    
    except:
        msg = 'Thêm nhà không thành công'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500

#---------------------------------------------------------------------------------------------------

@app.route('/api/home/camera', methods=['POST'])
def get_camera_in_home():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    homeid = data.get('homeid')
    print("homeid:", homeid, ' - ', type(homeid))

    home_info_list = []
    cursor.execute("SELECT CameraID, CameraName, HomeID, LockID, CamUsername, RTSP_encode FROM Camera WHERE HomeID = ?", homeid)
    results = cursor.fetchall()
    for i in results:
        
        cam_img = str(i.CameraID)
        cam_img_path = os.path.join(cam_img_folder_path, cam_img+'.jpg')
        if os.path.exists(cam_img_path):
            img = cv2.imread(cam_img_path)
        else:
            img = cv2.imread('cam_img/default.jpg')
        
        if img is None:
            img = cv2.imread('cam_img/default.jpg')
            
        _, image_data = cv2.imencode('.jpg', img)
        
        # Chuyển đổi dữ liệu ảnh thành chuỗi base64
        base64_image = base64.b64encode(image_data).decode("utf-8")
        
        #--------------------------------------------------------------------------
        
        # Nếu cam không có khóa
        if i.LockID==None:

            home_info_list.append({
                'CameraID': i.CameraID,
                'CameraName': i.CameraName,
                'LockID': None,
                'LockName': None,
                'CamUsername': i.CamUsername,
                'RTSP': aes_decrypt(i.RTSP_encode),
                'Hinh': base64_image,
            })
            
        # Nếu cam có khóa
        else:
            cursor.execute("SELECT LockName FROM Lock WHERE LockID = ?", i.LockID)
            lock = cursor.fetchone()
            #---------------------------------------------------------------------- 
            home_info_list.append({
                'CameraID': i.CameraID,
                'CameraName': i.CameraName,
                'LockID': i.LockID,
                'LockName': lock.LockName,
                'CamUsername': i.CamUsername,
                'RTSP': aes_decrypt(i.RTSP_encode),
                'Hinh': base64_image,
            })
            
    cursor.close()
    conn.close()
    print(f"Trả về list thông tin các camera của căn hộ có ID là {homeid}...")
    return json.dumps(home_info_list), 200
    
#---------------------------------------------------------------------------------------------------

####################################################################################################

@app.route('/api/lock/all-lock', methods=['POST'])
def all_lock():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400

    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    home_info_list, all_lock = [], []
    
    #-------------------------------------------------
    # Lấy CustomerID
    try:
        # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
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
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    #---------------------------------------------------------------------------------------
    # LẤY NHÀ CỦA USER
    try:
        cursor.execute("SELECT HomeName, HomeAddress, DistrictID, HomeID FROM CustomerHome WHERE CustomerID = ?", customerid)
        results = cursor.fetchall()
        # Chuyển danh sách các tuple thành danh sách các dictionary
        
        for result in results:
            home_info_list.append({
                'HomeName': result.HomeName,
                'HomeAddress': result.HomeAddress,
                'DistrictID': result.DistrictID,
                'HomeID': result.HomeID,
                'Owner': '1',
            })
    except:
        msg = f"Lỗi! Không lấy được thông tin các căn hộ của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
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
                'HomeName': results_.HomeName,
                'HomeAddress': results_.HomeAddress,
                'DistrictID': results_.DistrictID,
                'HomeID': homeid,
                'Owner': '0',
            })
    except:
        msg = f"Lỗi! Không lấy được thông tin các căn hộ User {ten_tai_khoan_email_sdt} được thêm vào"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    #---------------------------------------------------------------------------------------
    # LẤY THÔNG TIN TẤT CẢ CÁC KHÓA
    for home in home_info_list:
        cursor.execute("SELECT LockID, LockName, LockStatus FROM Lock WHERE HomeID = ?", home['HomeID'])
        results = cursor.fetchall()
        # Chuyển danh sách các tuple thành danh sách các dictionary
        for result in results:
            all_lock.append({
                'HomeName': home['HomeName'],
                'HomeAddress': home['HomeAddress'],
                'DistrictID': home['DistrictID'],
                'HomeID': home['HomeID'],
                'Owner': home['Owner'],
                
                'LockID': result.LockID,
                'LockName': result.LockName,
                'LockStatus': result.LockStatus if result.LockStatus!=None else 'Unknown',
            })
    
    cursor.close()
    conn.close()
    return json.dumps(all_lock), 200
#---------------------------------------------------------------------------------------------------
  
@app.route('/api/lock/lockinfo', methods=['POST'])
def lockinfo():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    # homename = data.get('homename')
    homeid = data.get('homeid')

    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    # print("homename:", homename, ' - ', type(homename))
    print("homeid:", homeid, ' - ', type(homeid))
    #-------------------------------------------------
    # Lấy CustomerID
    try:
        # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
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
        cursor.close()
        conn.close()
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
        cursor.close()
        conn.close()
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
                cursor.close()
                conn.close()
                return json.dumps(lock_info_list), 200
        except:
            msg = "Lỗi! Không lấy được thông tin các khóa"
            print(msg)
            cursor.close()
            conn.close()
            return jsonify({'message': msg}), 404

#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/delete-lock', methods=['POST'])
def delete_lock(): 
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    lockid = data.get('lockid')
    print("lockid:", lockid, ' - ', type(lockid))
    
    # Xóa khóa (Lock)
    try:
        # cursor.execute("SELECT LockName FROM Lock WHERE LockID = ?", lockid)
        # if cursor.fetchone():
        cursor.execute("DELETE FROM Lock WHERE LockID = ?", (lockid,))
        conn.commit()
        msg = f"Xóa thành công khóa {lockid} trong bảng Lock"
        print(msg)
        # return jsonify({'message': msg}), 200
    except Exception as e:
        conn.rollback()
        msg = f"Không xóa được khóa {lockid} trong bảng Lock"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500

    # Xóa khóa (Camera)
    try:
        cursor.execute("UPDATE Camera SET LockID = NULL WHERE LockID = ?", (lockid,))
        conn.commit()
        msg = f"Xóa thành công khóa {lockid} trong bảng Camera"
        print(msg)
    except Exception as e:
        conn.rollback()
        msg = f"Không xóa được khóa {lockid} trong bảng Lock"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    
    # Xóa khóa (LockHistory)
    try:
        cursor.execute("SELECT LockName FROM Lock WHERE LockID = ?", (lockid,))
        if cursor.fetchone():
            cursor.execute("DELETE FROM LockHistory WHERE LockID = ?", (lockid,))
            msg = f"Xóa thành công khóa {lockid} trong bảng LockHistory"
            print(msg)
            cursor.close()
            conn.close()
            return jsonify({'message': msg}), 200
        else:
            msg = f"Khóa {lockid} không có lịch sử để xóa"
            print(msg)
            cursor.close()
            conn.close()
            return jsonify({'message': msg}), 200
    except Exception as e:
        conn.rollback()
        msg = f"Không xóa được khóa {lockid} trong bảng LockHistory"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/addlock', methods=['POST'])
def addlock():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    lockid = data.get('lockid')
    camera_id = data.get('camera_id', None)
    lockname = data.get('lockname')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    homename = data.get('homename')

    print("lockid:", lockid, ' - ', type(lockid))
    print("camera_id:", camera_id, ' - ', type(camera_id))
    print("lockname:", lockname, ' - ', type(lockname))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("homename:", homename, ' - ', type(homename))
    
    #-------------------------------------------------
    try:
        # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
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
        msg = 'Không lấy được HomeID từ customer_id và homename'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    
    #-------------------------------------------------
    # Kiểm tra nếu LockID đúng
    cursor.execute("SELECT * FROM ActiveLock WHERE LockID = ?", (lockid,))
    right_lockid = cursor.fetchone()
    if right_lockid:
        pass
    else:     
        msg = 'Sai LockID'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    
    #-------------------------------------------------
    
    # Kiểm tra nếu LockName đã tồn tại
    cursor.execute("SELECT * FROM Lock WHERE LockName = ? AND HomeID = ?", (lockname, homeid))
    if cursor.fetchall():
        msg = 'Trùng tên khóa'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    
    #-------------------------------------------------
    
    # Kiểm tra nếu LockID đã tồn tại
    cursor.execute("SELECT * FROM Lock WHERE LockID = ? AND HomeID = ?", (lockid, homeid))
    if cursor.fetchall():
        msg = 'Khóa đã thêm trước đó'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    
    #-------------------------------------------------
    
    try:
        cursor.execute("INSERT INTO Lock (LockID, LockName, HomeID) VALUES (?, ?, ?)", (lockid, lockname, homeid))
        conn.commit()
        if camera_id is not None:
            cursor.execute("INSERT INTO Camera (LockID) VALUES (?)", (lockid,))
            conn.commit()
            print(f"Đã thêm khóa {lockid} và camera có ID {camera_id}")
        msg = 'Thêm khóa thành công'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 201
    except:
        msg = 'Thêm khóa không thành công'
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    
#---------------------------------------------------------------------------------------------------

# @app.route('/api/lock/addlock/camera-list', methods=['POST'])
# def addlock():
#     data = request.get_json()
#     key = data.get('key')
#     if key not in api_keys:
#         print('Sai key')
#         return jsonify({'message': 'Sai key'}), 400
    
#     homename = data.get('homename')
#     ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    
#     print("homename:", homename, ' - ', type(homename))
#     print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
#     #-------------------------------------------------
#     try:    
#         # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
#         if "@" in ten_tai_khoan_email_sdt:
#             cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
#         elif ten_tai_khoan_email_sdt.isdigit():
#             cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
#         else:
#             cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
#         results = cursor.fetchall()
#         customer_id = results[0][0]
        
#         # Từ CustomerID lấy HomeID trong bảng CustomerHome
#         cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ? AND HomeName = ?", (customer_id, homename))
#         results = cursor.fetchall()
#         homeid = results[0][0]
#     except:
#         msg = 'Không lấy được HomeID từ UserName'
#         print(msg)
#         return jsonify({'message': msg}), 500
    
#     #-------------------------------------------------
    
#     # Từ HomeID trong bảng CameraName, CameraID
#     cursor.execute("SELECT CameraName, CameraID FROM Camera WHERE HomeID = ?", (homeid,))
#     results = cursor.fetchall()
#     homeid = results[0][0]
       
####################################################################################################

@app.route('/api/lock/add-home-member', methods=['POST'])
def add_home_member():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    homemember = data.get('ten_tai_khoan_email_sdt_homemember')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    homename = data.get('homename')
    
    print("ten_tai_khoan_email_sdt_homemember:", homemember, ' - ', type(homemember))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("homename:", homename, ' - ', type(homename))
    
    #---------------------------------------------------------------------------------------
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID của admin trong bảng Customer
    try:
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
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    #---------------------------------------------------------------------------------------
    try:
        # Từ "homename" lấy HomeID của admin trong bảng CustomerHome
        cursor.execute("SELECT HomeID FROM CustomerHome WHERE HomeName = ? AND CustomerID = ?", (homename, admin_id))
        results = cursor.fetchall()
        homeid = results[0][0]
    except:
        # msg = f"Lỗi! Không lấy được HomeID của Admin {ten_tai_khoan_email_sdt}"
        msg = f"Lỗi! Không phải tài khoản Quản trị viên."
        print(msg)
        cursor.close()
        conn.close()
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
        msg = f"Lỗi! Không tìm thấy tài khoản {homemember}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    #---------------------------------------------------------------------------------------
    # Kiểm tra thêm quyền home-user này chưa
    cursor.execute("SELECT * FROM HomeMember WHERE HomeID = ? AND HomeMemberID = ?", (homeid, homemember_id))
    if cursor.fetchall():
        msg = f"Không thêm được. Trước đó đã thêm User {homemember} vào căn {homename}!"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    #---------------------------------------------------------------------------------------
    try:
        cursor.execute("INSERT INTO HomeMember (AdminID, HomeID, HomeMemberID) VALUES (?, ?, ?)",
                       (admin_id, homeid, homemember_id))
        conn.commit()
        msg = f"Đã thêm User {homemember} và căn hộ {homename} của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 201
    except:
        msg = f"Lỗi! Không thêm HomeMember được!"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/delete-home-member', methods=['POST'])
def delete_home_member():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    homeid = data.get('homeid')
    sdt = data.get('sdt')
    access_token = data.get('access_token')
    
    print("homeid:", homeid, ' - ', type(homeid))
    print("sdt:", sdt, ' - ', type(sdt))
    
    #---------------------------------------------------------------------------------------
    try:
        # Từ "sdt" lấy CustomerID của member trong bảng Customer
        cursor.execute("SELECT CustomerID, Username FROM Customer WHERE Mobile = ?", sdt)
        results = cursor.fetchone()
        member_id = results.CustomerID
        username = results.Username
    except:
        msg = f"Lỗi! Không lấy được CustomerID của Member {sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    #---------------------------------------------------------------------------------------
    try:
        # Xóa quyền
        cursor.execute("DELETE FROM HomeMember WHERE HomeMemberID = ? AND HomeID = ?", (member_id, homeid))
        conn.commit()
        msg = f"Đã xóa User {sdt} khỏi căn hộ {homeid} trong Database"
        print(msg)
    except:
        msg = f"Lỗi! Không xóa được User {sdt} khỏi căn hộ {homeid} trong Database"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    #---------------------------------------------------------------------------------------
    try:
        # Lấy danh sách các LockID trong căn hộ cần xóa quyền
        cursor.execute("SELECT LockID FROM Lock WHERE HomeID = ?", homeid)
        list_lockid = [row.LockID for row in cursor.fetchall()]
        
        #################### Xóa PassCode trên TTLock ####################
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        url = "https://euapi.sciener.com/v3/keyboardPwd/delete"

        for lock_id in list_lockid:      
            now = datetime.datetime.now()
            new_time = now + datetime.timedelta(seconds=2)
            timestamp = int(new_time.timestamp() * 1000)
            
            # Lấy PassCodeID từ "sdt" và "lock_id"
            cursor.execute(f"SELECT PassCodeID FROM PassCode WHERE LockID = ? AND Username = ?", (lock_id, username))
            result = cursor.fetchone()
            if result==None:
                continue
            passcode_id = result.PassCodeID
            data = {
                "clientId": '87ed6cf1e9274e65af6500193fd7dce8',
                "accessToken": access_token,
                "lockId": int(lock_id), #9399008,
                "keyboardPwdId": passcode_id,
                "deleteType": 2,
                "date": timestamp,
            }
            response = requests.post(url, headers=headers, data=data)
            if response.status_code == 200:
                try:
                    if response.json()['errcode']==0:
                        #################### Xóa PassCode trong Database SQL ####################
                        cursor.execute("DELETE FROM PassCode WHERE Username = ?", username)
                        conn.commit()
                        msg = f"Xóa thành công PassCode ở Lock {lock_id} của User {username}"
                        print(msg)
                    else:
                        errcode = response.json()['errcode']
                        # cursor.execute("SELECT Description FROM ErrorCode WHERE Code = ?", errcode)
                        # error = cursor.fetchone().Description
                        cursor.execute("SELECT MoTa FROM ErrorCode WHERE Code = ?", errcode)
                        error = cursor.fetchone().MoTa
                        print(error)
                        cursor.close()
                        conn.close()
                        return Response(error, mimetype='text/plain')
                    
                except Exception as e:
                    print(e)
                    msg = f"Lỗi! Chưa xóa được PassCode ở Lock {lock_id} của User {username} trong Database"
                    print(msg)
        msg = "Đã xóa xong"
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 200
    except:
        msg = f"Lỗi! Không xóa được User {username} khỏi căn hộ {homeid}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/home-member-list', methods=['POST'])
def home_member_list():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    homeid = data.get('homeid')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    
    print("homeid:", homeid, ' - ', type(homeid))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))

    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID của admin trong bảng Customer
    try:
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
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    #---------------------------------------------------------------------------------------
    # # Kiểm tra "ten_tai_khoan_email_sdt" có phải admin của căn hộ không
    # cursor.execute("SELECT * FROM CustomerHome WHERE HomeID = ? AND CustomerID = ?", (homeid, admin_id))
    # if not cursor.fetchall():
    #     member_list = []
    #     member_list.append({
    #             'Username': 'Không phải Admin',
    #             'Email': 'Không phải Admin',
    #             'Mobile': 'Không phải Admin',
    #             'FullName': 'Không phải Admin'
    #         })
    #     print(f"Đây không phải tài khoản Admin")
    #     return json.dumps(member_list), 200
    #---------------------------------------------------------------------------------------
    try:
        member_list = []
        # Lấy danh sách member
        cursor.execute("SELECT HomeMemberID FROM HomeMember WHERE AdminID = ? AND HomeID = ?", (admin_id, homeid))
        members = cursor.fetchall()
        for member_id in members:
            cursor.execute("SELECT Username, Email, Mobile, FullName FROM Customer WHERE CustomerID = ?", member_id[0])
            result = cursor.fetchone()
            member_list.append({
                'Username': result.Username,
                'Email': result.Email,
                'Mobile': result.Mobile,
                'FullName': result.FullName,
            })
        print(f"Trả về list các User được thêm quyền của căn hộ {homeid}...")
        cursor.close()
        conn.close()
        return json.dumps(member_list), 200
    except:
        msg = f"Lỗi! Không lấy được list các User được thêm quyền của căn hộ {homeid}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
####################################################################################################

@app.route('/api/lock/updatehistory', methods=['POST'])
def update_history():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400

    # Lấy dữ liệu từ request
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    lock_id = data.get('lock_id')
    history_code = data.get('history_code')
    
    current_datetime = datetime.datetime.now()
    # history_date_str = current_datetime.strftime("%Y-%m-%d %H:%M:%S") # String -> "2023-07-21 15:30:00"
    
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("lock_id:", lock_id, ' - ', type(lock_id))
    print("history_code:", history_code, ' - ', type(history_code))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404

    # Xác định HistoryDescription
    if history_code==0:
        history_description = "Mở khóa thành công"
    else:
        # cursor.execute("SELECT Description FROM ErrorCode WHERE Code = ?", history_code)
        # history_description = "Lỗi: " + cursor.fetchone().Description
        cursor.execute("SELECT MoTa FROM ErrorCode WHERE Code = ?", history_code)
        history_description = "Lỗi: " + cursor.fetchone().MoTa
        
    # Chuyển đổi định dạng datetime
    # try:
    #     history_date = datetime.datetime.strptime(history_date_str, "%Y-%m-%d %H:%M:%S")
    # except ValueError:
    #     msg = "Invalid HistoryDate format. It should be in format 'YYYY-MM-DD HH:MM:SS'"
    #     print(msg)
    #     return jsonify({"error": msg}), 400

    # Lấy FullName từ Username
    try:
        cursor.execute("SELECT FullName FROM Customer WHERE Username = ?", username)
        fullname = cursor.fetchone()[0]
    except ValueError:
        msg = f"User {username} không có FullName"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({"error": msg}), 400
    
    # Thêm dữ liệu vào bảng 'LockHistory' trong CSDL
    cursor.execute("INSERT INTO LockHistory (LockID, HistoryDescription, HistoryCode, HistoryDate, FullName, Username) VALUES (?, ?, ?, ?, ?, ?)", 
                   (lock_id, history_description, history_code, current_datetime, fullname, username))
    conn.commit()
    msg = "LockHistory updated successfully"
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({"message": msg}), 201

#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/get-history', methods=['POST'])
def get_history():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400

    lock_id = data.get('lock_id')
    history_list = []
    try:
        cursor.execute("SELECT Username, HistoryDescription, HistoryDate FROM LockHistory WHERE LockID = ? ORDER BY HistoryDate DESC", lock_id)
        history = cursor.fetchall()
        for i in history:
            history_list.append({
                'Username': i.Username,
                'HistoryDescription': i.HistoryDescription,
                # 'HistoryCode': i[2],
                'HistoryDate': i.HistoryDate.strftime("%Y-%m-%d %H:%M:%S"),
            })
        print(f"Trả về lịch sử khóa {lock_id}")
        cursor.close()
        conn.close()
        return json.dumps(history_list), 200
    except Exception as e:
        print(e)

####################################################################################################

@app.route('/api/lock/check-existed-passcode', methods=['POST'])
def check_existed_passcode():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    lock_id = data.get('lockid')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    
    print("lockid:", lock_id, ' - ', type(lock_id))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
        customerid = cursor.fetchone().CustomerID
        cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    cursor.execute("SELECT * FROM PassCode WHERE LockID = ? AND Username = ? ", (lock_id, username))
    results = cursor.fetchone()
    if results:
        print(results.PassCode)
        cursor.close()
        conn.close()
        return Response(results.PassCode, mimetype='text/plain')
    else:
        print("Đặt PassCode")
        cursor.close()
        conn.close()
        return Response("1", mimetype='text/plain')
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/add-custom-passcode', methods=['POST'])
def add_custom_passcode():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    lock_id = data.get('lockid')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    passcode = data.get('passcode')
    access_token = data.get('access_token')
    
    print("lockid:", lock_id, ' - ', type(lock_id))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("passcode:", passcode, ' - ', type(passcode))

    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    url = "https://euapi.sciener.com/v3/keyboardPwd/add"

    now = datetime.datetime.now()
    new_time = now + datetime.timedelta(seconds=2)
    timestamp = int(new_time.timestamp() * 1000)
        
    data = {
        "clientId": '87ed6cf1e9274e65af6500193fd7dce8',
        "accessToken": access_token,
        "lockId": int(lock_id), #9399008,
        "keyboardPwdType": 2,
        "keyboardPwd": passcode,
        "keyboardPwdName": "PassCode của " + username,
        "addType": 2,
        "date": timestamp,
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        try:
            errcode = response.json()['errcode']
            # cursor.execute("SELECT Description FROM ErrorCode WHERE Code = ?", errcode)
            # error = cursor.fetchone().Description
            cursor.execute("SELECT MoTa FROM ErrorCode WHERE Code = ?", errcode)
            error = cursor.fetchone().MoTa
            print(error)
            cursor.close()
            conn.close()
            return Response(error, mimetype='text/plain')
        except:
            passcode_id =  response.json()['keyboardPwdId']
            #-----------------------------------------
            # Từ LockID lấy ra Owner, HomeName và HomeID
            # cursor.execute(f"""
            #                     SELECT C.Username, CH.HomeName, CH.HomeID
            #                     FROM Lock_Camera LC
            #                     JOIN Lock L ON LC.LockID = L.LockID
            #                     JOIN CustomerHome CH ON L.HomeID = CH.HomeID
            #                     JOIN Customer C ON CH.CustomerID = C.CustomerID
            #                     WHERE LC.LockID = {lock_id}
            #                 """)
            #-----------------------------------------
            # Từ LockID lấy ra Owner, HomeName và HomeID
            cursor.execute(f"""
                                SELECT C.Username, CH.HomeName, CH.HomeID
                                FROM Camera CAM
                                JOIN Lock L ON CAM.LockID = L.LockID
                                JOIN CustomerHome CH ON L.HomeID = CH.HomeID
                                JOIN Customer C ON CH.CustomerID = C.CustomerID
                                WHERE CAM.LockID = {lock_id}
                            """)
            row = cursor.fetchone()
            if row:
                owner, homename, homeid = row
            cursor.execute("INSERT INTO PassCode (LockID, PassCode, Username, PassCodeID, Owner, HomeName, HomeID) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                    (lock_id, passcode, username, passcode_id, owner, homename, homeid))
            conn.commit()
            msg = "Đặt PassCode thành công!"
            print(msg)
            cursor.close()
            conn.close()
            return Response(msg, mimetype='text/plain')
    else:
        msg = "Failed"
        print(msg)
        cursor.close()
        conn.close()
        return Response(msg, mimetype='text/plain')
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/change-passcode', methods=['POST'])
def change_passcode():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    lock_id = data.get('lockid')
    new_passcode = data.get('new_passcode')
    access_token = data.get('access_token')
    
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("lockid:", lock_id, ' - ', type(lock_id))
    print("new_passcode:", new_passcode, ' - ', type(new_passcode))

    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    url = "https://euapi.sciener.com/v3/keyboardPwd/change"

    now = datetime.datetime.now()
    new_time = now + datetime.timedelta(seconds=2)
    timestamp = int(new_time.timestamp() * 1000)
    
    # Lấy PassCodeID
    cursor.execute("SELECT PassCodeID FROM PassCode WHERE Username = ?", username)
    passcode_id = cursor.fetchone().PassCodeID
    
    data = {
        "clientId": '87ed6cf1e9274e65af6500193fd7dce8',
        "accessToken": access_token,
        "lockId": 9399008,
        "keyboardPwdId": passcode_id,
        "newKeyboardPwd": new_passcode,
        # "startDate": timestamp,
        # "endDate": timestamp+50000,
        "changeType": 2,
        "date": timestamp,
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        try:
            if response.json()['errcode']==0:
                #################### Đổi PassCode trong Database SQL ####################
                cursor.execute("UPDATE PassCode SET PassCode = ? WHERE Username = ?", (new_passcode, username))
                conn.commit()
                msg = f"Đổi thành công PassCode của User {username}"
                print(msg)
                cursor.close()
                conn.close()
                return Response("Đã đổi PassCode", mimetype='text/plain')
            else:
                # Trả về lỗi trong ds lỗi TTLock
                errcode = response.json()['errcode']
                # cursor.execute("SELECT Description FROM ErrorCode WHERE Code = ?", errcode) # Tiếng Anh
                error = cursor.fetchone().Description
                cursor.execute("SELECT MoTa FROM ErrorCode WHERE Code = ?", errcode) # Tiếng Việt
                error = cursor.fetchone().MoTa
                print(error)
                cursor.close()
                conn.close()
                return Response(error, mimetype='text/plain')
            
        except Exception as e:
            print(e)
            cursor.close()
            conn.close()
            return Response("Lỗi! Chưa đổi được PassCode trong Database", mimetype='text/plain')
    else:
        msg = f"Lỗi! Chưa đổi được PassCode của User {username}"
        print(msg)
        cursor.close()
        conn.close()
        return Response(msg, mimetype='text/plain')
#---------------------------------------------------------------------------------------------------

@app.route('/api/lock/delete-passcode', methods=['POST'])
def delete_passcode():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    lock_id = data.get('lockid')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    access_token = data.get('access_token')
    
    print("lockid:", lock_id, ' - ', type(lock_id))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    #################### Xóa PassCode trên TTLock ####################
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    url = "https://euapi.sciener.com/v3/keyboardPwd/delete"

    now = datetime.datetime.now()
    new_time = now + datetime.timedelta(seconds=2)
    timestamp = int(new_time.timestamp() * 1000)
    
    # Lấy PassCodeID
    cursor.execute("SELECT PassCodeID FROM PassCode WHERE Username = ?", username)
    passcode_id = cursor.fetchone().PassCodeID
    data = {
        "clientId": '87ed6cf1e9274e65af6500193fd7dce8',
        "accessToken": access_token,
        "lockId": int(lock_id), #9399008,
        "keyboardPwdId": passcode_id,
        "deleteType": 2,
        "date": timestamp,
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        try:
            if response.json()['errcode']==0:
                #################### Xóa PassCode trong Database SQL ####################
                cursor.execute("DELETE FROM PassCode WHERE Username = ?", username)
                conn.commit()
                msg = f"Xóa thành công PassCode của User {username}"
                print(msg)
                cursor.close()
                conn.close()
                return Response("Đã xóa PassCode", mimetype='text/plain')
            else:
                # Trả về lỗi trong ds lỗi TTLock
                errcode = response.json()['errcode']
                # cursor.execute("SELECT Description FROM ErrorCode WHERE Code = ?", errcode)
                # error = cursor.fetchone().Description
                cursor.execute("SELECT MoTa FROM ErrorCode WHERE Code = ?", errcode)
                error = cursor.fetchone().MoTa
                print(error)
                cursor.close()
                conn.close()
                return Response(error, mimetype='text/plain')
            
        except Exception as e:
            print(e)
            cursor.close()
            conn.close()
            return Response("Lỗi! Chưa xóa được PassCode trong Database", mimetype='text/plain')
    else:
        msg = f"Lỗi! Chưa xóa được PassCode của User {username}"
        print(msg)
        cursor.close()
        conn.close()
        return Response(msg, mimetype='text/plain')

####################################################################################################

@app.route('/api/camera/add', methods=['POST'])
def add_camera():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    camera_name = data.get('camera_name')
    homename = data.get('homename')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    cam_username = data.get('cam_username')
    cam_pass = data.get('cam_pass')
    ddns = data.get('ddns')
    port = data.get('port')
    
    print("camera_name:", camera_name, ' - ', type(camera_name))
    print("homename:", homename, ' - ', type(homename))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("cam_username:", cam_username, ' - ', type(cam_username))
    print("cam_pass:", cam_pass, ' - ', type(cam_pass))
    print("ddns:", ddns, ' - ', type(ddns))

    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    # Từ CustomerID lấy HomeID trong bảng CustomerHome
    cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ? AND HomeName = ?", (customerid, homename))
    results = cursor.fetchall()
    homeid = results[0][0]

    rtsp = aes_encrypt(f'rtsp://{cam_username}:{cam_pass}@{ddns}:{port}/cam/realmonitor?channel=1&subtype=0&unicast=true')
    
    # Lưu vào bảng Camera
    cursor.execute("INSERT INTO Camera (CameraName, HomeID, Username, CamUsername, CamPass, RTSP_encode) VALUES (?, ?, ?, ?, ?, ?)",
                   (camera_name, homeid, username, cam_username, cam_pass, rtsp))
    conn.commit()
    
    msg = f"Đã thêm cam cho User {ten_tai_khoan_email_sdt}"
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 201

# #---------------------------------------------------------------------------------------------------

@app.route('/api/camera/edit', methods=['POST'])
def edit_camera():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    camera_id = data.get('camera_id')
    camera_name = data.get('camera_name')
    homename = data.get('homename')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    cam_username = data.get('cam_username')
    cam_pass = data.get('cam_pass')
    ddns = data.get('ddns')
    port = data.get('port')
    
    print("camera_name:", camera_name, ' - ', type(camera_name))
    print("homename:", homename, ' - ', type(homename))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("cam_username:", cam_username, ' - ', type(cam_username))
    print("cam_pass:", cam_pass, ' - ', type(cam_pass))
    print("ddns:", ddns, ' - ', type(ddns))

    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    # Từ CustomerID lấy HomeID trong bảng CustomerHome
    cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ? AND HomeName = ?", (customerid, homename))
    results = cursor.fetchall()
    homeid = results[0][0]
    
    rtsp = aes_encrypt(f'rtsp://{cam_username}:{cam_pass}@{ddns}:{port}/cam/realmonitor?channel=1&subtype=0&unicast=true')
    
    # Lưu vào bảng Camera
    cursor.execute("UPDATE Camera SET CameraName=?, HomeID=?, Username=?, CamUsername=?, CamPass=?, RTSP_encode=? WHERE CameraID=?",
                    (camera_name, homeid, username, cam_username, cam_pass, rtsp, camera_id))
    conn.commit()
    
    msg = f"Đã sửa thông tin cam của User {ten_tai_khoan_email_sdt}"
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 200

# #---------------------------------------------------------------------------------------------------

# @app.route('/api/camera/add-existed-lock-to-cam', methods=['POST'])
# def add_camera():
#     conn = connect_to_database()
#     cursor = conn.cursor()
#     data = request.get_json()
#     key = data.get('key')
#     if key not in api_keys:
#         print('Sai key')
#         cursor.close()
#         conn.close()
#         return jsonify({'message': 'Sai key'}), 400
    
#     camera_id = data.get('camera_id')
#     lock_id = data.get('lock_id')
    
#     print("camera_id:", camera_id, ' - ', type(camera_id))
#     print("lock_id:", lock_id, ' - ', type(lock_id))


#     # Lưu vào bảng Camera
#     cursor.execute("UPDATE Camera SET LockID = ? WHERE HomeID = ?",
#                    (lock_id, camera_id))
    
#     conn.commit()
#     msg = f"Đã thêm khóa {ten_tai_khoan_email_sdt}"
#     print(msg)
#     cursor.close()
#     conn.close()
#     return jsonify({'message': msg}), 404
#---------------------------------------------------------------------------------------------------

@app.route('/api/camera/get-user-camera', methods=['POST'])
def get_camera():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
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
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    # Lấy danh sách camera của User
    camera_list = []
    # try:
    # Lấy cam của User
    cursor.execute(f"""
                        SELECT cam.LockID, cam.CameraID, cam.HomeID
                        FROM Camera cam
                        JOIN CustomerHome ch ON cam.HomeID = ch.HomeID
                        WHERE ch.CustomerID = '{customer_id}'
                    """)
    result_1 = cursor.fetchall()
    
    # Lấy cam được thêm quyền
    cursor.execute(f"""
                        SELECT cam.LockID, cam.CameraID, cam.HomeID
                        FROM Camera cam
                        JOIN HomeMember hm ON cam.HomeID = hm.HomeID
                        WHERE hm.HomeMemberID = {customer_id}
                    """)
    result_2 = cursor.fetchall()
    
    results = result_1 + result_2
    
    for i in results:
            
        cursor.execute("SELECT CameraName, RTSP_encode FROM Camera WHERE CameraID = ?", i.CameraID)
        cam = cursor.fetchone()
        cam_img = str(i.CameraID)
        cam_img_path = os.path.join(cam_img_folder_path, cam_img+'.jpg')
        if os.path.exists(cam_img_path):
            img = cv2.imread(cam_img_path)
        else:
            img = cv2.imread('cam_img/default.jpg')
        
        if img is None:
            img = cv2.imread('cam_img/default.jpg')

        _, image_data = cv2.imencode('.jpg', img)
        
        # Chuyển đổi dữ liệu ảnh thành chuỗi base64
        base64_image = base64.b64encode(image_data).decode("utf-8")
        #--------------------------------------------------------------------------
        
        # Nếu cam không có khóa
        if i.LockID==None:
            camera_list.append({
                'HomeID': i.HomeID,
                'CameraID': i.CameraID,
                'LockID': None,
                'LockName': None,
                'CameraName': cam.CameraName,
                'RTSP': aes_decrypt(cam.RTSP_encode),
                'Hinh': base64_image,
            })
            
        # Nếu cam có khóa
        else:
            cursor.execute("SELECT LockName FROM Lock WHERE LockID = ?", i.LockID)
            lock = cursor.fetchone()
            #----------------------------------------------------------------------        
            camera_list.append({
                'HomeID': i.HomeID,
                'CameraID': i.CameraID,
                'LockID': i.LockID,
                'LockName': lock.LockName,
                'CameraName': cam.CameraName,
                'RTSP': aes_decrypt(cam.RTSP_encode),
                'Hinh': base64_image,
            })

    # except Exception as e:
    #     msg = f"Lỗi! Không lấy được danh sách camera của user {ten_tai_khoan_email_sdt}"
    #     print(msg)
    #     cursor.close()
    #     conn.close()
    #     return jsonify({'message': msg}), 404
    
    # for camera in camera_list:
    #     # Làm mới Thumbnail
    #     save_thumbnail(camera['RTSP'], camera['CameraID'])
    
    try:
        type_list = ['Pose', 'Fire', 'Smoke']
        placeholders = ", ".join(["?" for _ in type_list])
        for camera in camera_list:
            # Thêm trường HomeName cho mỗi Cam
            cursor.execute("SELECT HomeName FROM CustomerHome WHERE HomeID = ?", (camera['HomeID'], ))
            camera['HomeName'] = cursor.fetchone().HomeName
            
            # Thêm trường LastestAlert và Date cho mỗi Cam
            cam_id = camera['CameraID']
            cursor.execute(f"SELECT TOP 1 * FROM Notification WHERE CameraID = ? AND Type IN ({placeholders}) ORDER BY Date DESC", (cam_id, *type_list))
            row = cursor.fetchone()
            if row:
                camera['ID_LastestAlert'] = row.ID_Notification
                camera['LastestAlert'] = row.Body
                # camera['Date'] = " - " + row.Date.strftime("%Y-%m-%d %H:%M:%S")
                camera['Date'] = " - " + row.Date.strftime("%d-%m-%Y %Hh%M'%S\"")
            else:
                camera['ID_LastestAlert'] = None
                camera['LastestAlert'] = None
                camera['Date'] = None
                
        print(f"Trả về danh sách camera và cảnh báo mới nhất của user {ten_tai_khoan_email_sdt}")
        cursor.close()
        conn.close()
        return json.dumps(camera_list), 200
    except Exception as e:
        msg = f"Lỗi! Không lấy được các cảnh báo mới nhất"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404

#---------------------------------------------------------------------------------------------------

####################################################################################################

@app.route('/api/notification/alert/get-by-camera', methods=['POST'])
def alert_get_by_camera():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    # ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    # print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    camera_id = data.get('camera_id')
    print("camera_id:", camera_id, ' - ', type(camera_id))
    # try:
    cursor.execute("SELECT * FROM Notification WHERE CameraID = ? ORDER BY Date DESC", camera_id)
    notifications = cursor.fetchall()
    notification_list = []
    for notification in notifications:
        if notification.Type in ["Pose", "Fire", "Smoke"]:
            notification_list.append({
                'ID_Notification': notification.ID_Notification,
                'Type': notification.Type,
                'Title': notification.Title,
                'Body': notification.Body,
                'Date': notification.Date.strftime("%d-%m-%Y %Hh%M'%S\""),
                
            })
    
    # Trả về trường "Seen" để biết thông báo đã xem chưa
    for i in notification_list:
        cursor.execute("SELECT * FROM Seen WHERE ID_Notification = ?", i['ID_Notification'])
        if cursor.fetchone():
            i['Seen'] = 'True'
        else:
            i['Seen'] = 'False'
            
    print(f"Trả về list các cảnh báo của Camera {camera_id}...")
    cursor.close()
    conn.close()
    return json.dumps(notification_list), 200
    # except:
    #     msg = f"Lỗi! Không lấy được list các thông báo của User {username}"
    #     print(msg)
    #     return jsonify({'message': msg}), 404

#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/pose/get-by-camera', methods=['POST'])
def pose_get_by_camera():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    # ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    # print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    camera_id = data.get('camera_id')
    print("camera_id:", camera_id, ' - ', type(camera_id))
    # try:
    cursor.execute("SELECT * FROM Notification WHERE CameraID = ? ORDER BY Date DESC", camera_id)
    notifications = cursor.fetchall()
    notification_list = []
    for notification in notifications:
        if notification.Type in ["Pose"]:
            notification_list.append({
                'ID_Notification': notification.ID_Notification,
                'Type': notification.Type,
                'Title': notification.Title,
                'Body': notification.Body,
                'Date': notification.Date.strftime("%d-%m-%Y %Hh%M'%S\""),
                
            })
    
    # Trả về trường "Seen" để biết thông báo đã xem chưa
    for i in notification_list:
        cursor.execute("SELECT * FROM Seen WHERE ID_Notification = ?", i['ID_Notification'])
        if cursor.fetchone():
            i['Seen'] = 'True'
        else:
            i['Seen'] = 'False'
            
    print(f"Trả về list các cảnh báo của Camera {camera_id}...")
    cursor.close()
    conn.close()
    return json.dumps(notification_list), 200
    # except:
    #     msg = f"Lỗi! Không lấy được list các thông báo của User {username}"
    #     print(msg)
    #     return jsonify({'message': msg}), 404

#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/fire/get-by-camera', methods=['POST'])
def fire_get_by_camera():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    # ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    # print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    camera_id = data.get('camera_id')
    print("camera_id:", camera_id, ' - ', type(camera_id))
    # try:
    cursor.execute("SELECT * FROM Notification WHERE CameraID = ? ORDER BY Date DESC", camera_id)
    notifications = cursor.fetchall()
    notification_list = []
    for notification in notifications:
        if notification.Type in ["Fire", "Smoke"]:
            notification_list.append({
                'ID_Notification': notification.ID_Notification,
                'Type': notification.Type,
                'Title': notification.Title,
                'Body': notification.Body,
                'Date': notification.Date.strftime("%d-%m-%Y %Hh%M'%S\""),
                
            })
    
    # Trả về trường "Seen" để biết thông báo đã xem chưa
    for i in notification_list:
        cursor.execute("SELECT * FROM Seen WHERE ID_Notification = ?", i['ID_Notification'])
        if cursor.fetchone():
            i['Seen'] = 'True'
        else:
            i['Seen'] = 'False'
            
    print(f"Trả về list các cảnh báo của Camera {camera_id}...")
    cursor.close()
    conn.close()
    return json.dumps(notification_list), 200
    # except:
    #     msg = f"Lỗi! Không lấy được list các thông báo của User {username}"
    #     print(msg)
    #     return jsonify({'message': msg}), 404

#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/alert/get-by-user', methods=['POST'])
def alert_get_by_user():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    # camera_id = data.get('camera_id')
    # print("camera_id:", camera_id, ' - ', type(camera_id))

    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        # cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        # username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    # Lấy ID nhà
    cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ?", (customerid,))
    home_ids = [row.HomeID for row in cursor.fetchall()]
    # Lấy ID nhà được thêm quyền
    cursor.execute("SELECT HomeID FROM HomeMember WHERE HomeMemberID = ?", (customerid,))
    home_ids = home_ids + [row.HomeID for row in cursor.fetchall()]
    
    # Lặp qua từng HomeID và lấy danh sách CameraID từ đó
    camera_ids = []
    for home_id in home_ids:
        cursor.execute("SELECT CameraID FROM Camera WHERE HomeID = ?", (home_id,))
        camera_ids.extend([row.CameraID for row in cursor.fetchall()])
    
    # try:
    params = ','.join('?' for _ in camera_ids)
    # cursor.execute(f"SELECT * FROM Notification WHERE CameraID IN ({params}) ORDER BY Date DESC", camera_id)
    cursor.execute(f"""
                        SELECT n.ID_Notification, n.CameraID, n.Type, n.Title, n.Body, n.Date, n.ImagePath, c.CameraName                     
                        FROM Notification n
                        INNER JOIN Camera c ON n.CameraID = c.CameraID
                        WHERE n.CameraID IN ({params})
                        ORDER BY n.Date DESC
                    """, camera_ids)
    notifications = cursor.fetchall()
    notification_list = []
    for notification in notifications:
        if notification.Type in ["Pose", "Fire", "Smoke"]:
            notification_list.append({
                'CameraID': notification.CameraID,
                'CameraName': notification.CameraName,
                'ID_Notification': notification.ID_Notification,
                'Type': notification.Type,
                'Title': notification.Title,
                'Body': notification.Body,
                'Date': notification.Date.strftime("%d-%m-%Y %Hh%M'%S\""),
            })
        
    # Trả về trường "Seen" để biết thông báo đã xem chưa
    for i in notification_list:
        cursor.execute("SELECT * FROM Seen WHERE ID_Notification = ?", i['ID_Notification'])
        if cursor.fetchone():
            i['Seen'] = 'True'
        else:
            i['Seen'] = 'False'
            
    print(f"Trả về list các cảnh báo của User {ten_tai_khoan_email_sdt}...")
    cursor.close()
    conn.close()
    return json.dumps(notification_list), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/pose/get-by-user', methods=['POST'])
def pose_get_by_user():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    # camera_id = data.get('camera_id')
    # print("camera_id:", camera_id, ' - ', type(camera_id))

    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        # cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        # username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    # Lấy ID nhà
    cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ?", (customerid,))
    home_ids = [row.HomeID for row in cursor.fetchall()]
    # Lấy ID nhà được thêm quyền
    cursor.execute("SELECT HomeID FROM HomeMember WHERE HomeMemberID = ?", (customerid,))
    home_ids = home_ids + [row.HomeID for row in cursor.fetchall()]
    
    # Lặp qua từng HomeID và lấy danh sách CameraID từ đó
    camera_ids = []
    for home_id in home_ids:
        cursor.execute("SELECT CameraID FROM Camera WHERE HomeID = ?", (home_id,))
        camera_ids.extend([row.CameraID for row in cursor.fetchall()])
    
    # try:
    params = ','.join('?' for _ in camera_ids)
    # cursor.execute(f"SELECT * FROM Notification WHERE CameraID IN ({params}) ORDER BY Date DESC", camera_id)
    cursor.execute(f"""
                        SELECT n.ID_Notification, n.CameraID, n.Type, n.Title, n.Body, n.Date, n.ImagePath, c.CameraName                     
                        FROM Notification n
                        INNER JOIN Camera c ON n.CameraID = c.CameraID
                        WHERE n.CameraID IN ({params})
                        ORDER BY n.Date DESC
                    """, camera_ids)
    notifications = cursor.fetchall()
    notification_list = []
    for notification in notifications:
        if notification.Type in ["Pose"]:
            notification_list.append({
                'CameraID': notification.CameraID,
                'CameraName': notification.CameraName,
                'ID_Notification': notification.ID_Notification,
                'Type': notification.Type,
                'Title': notification.Title,
                'Body': notification.Body,
                'Date': notification.Date.strftime("%d-%m-%Y %Hh%M'%S\""),
            })
        
    # Trả về trường "Seen" để biết thông báo đã xem chưa
    for i in notification_list:
        cursor.execute("SELECT * FROM Seen WHERE ID_Notification = ?", i['ID_Notification'])
        if cursor.fetchone():
            i['Seen'] = 'True'
        else:
            i['Seen'] = 'False'
            
    print(f"Trả về list các cảnh báo của User {ten_tai_khoan_email_sdt}...")
    cursor.close()
    conn.close()
    return json.dumps(notification_list), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/fire/get-by-user', methods=['POST'])
def fire_get_by_user():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    # camera_id = data.get('camera_id')
    # print("camera_id:", camera_id, ' - ', type(camera_id))

    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        # cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        # username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    # Lấy ID nhà
    cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ?", (customerid,))
    home_ids = [row.HomeID for row in cursor.fetchall()]
    # Lấy ID nhà được thêm quyền
    cursor.execute("SELECT HomeID FROM HomeMember WHERE HomeMemberID = ?", (customerid,))
    home_ids = home_ids + [row.HomeID for row in cursor.fetchall()]
    
    # Lặp qua từng HomeID và lấy danh sách CameraID từ đó
    camera_ids = []
    for home_id in home_ids:
        cursor.execute("SELECT CameraID FROM Camera WHERE HomeID = ?", (home_id,))
        camera_ids.extend([row.CameraID for row in cursor.fetchall()])
    
    # try:
    params = ','.join('?' for _ in camera_ids)
    # cursor.execute(f"SELECT * FROM Notification WHERE CameraID IN ({params}) ORDER BY Date DESC", camera_id)
    cursor.execute(f"""
                        SELECT n.ID_Notification, n.CameraID, n.Type, n.Title, n.Body, n.Date, n.ImagePath, c.CameraName                     
                        FROM Notification n
                        INNER JOIN Camera c ON n.CameraID = c.CameraID
                        WHERE n.CameraID IN ({params})
                        ORDER BY n.Date DESC
                    """, camera_ids)
    notifications = cursor.fetchall()
    notification_list = []
    for notification in notifications:
        if notification.Type in ["Fire", "Smoke"]:
            notification_list.append({
                'CameraID': notification.CameraID,
                'CameraName': notification.CameraName,
                'ID_Notification': notification.ID_Notification,
                'Type': notification.Type,
                'Title': notification.Title,
                'Body': notification.Body,
                'Date': notification.Date.strftime("%d-%m-%Y %Hh%M'%S\""),
            })
        
    # Trả về trường "Seen" để biết thông báo đã xem chưa
    for i in notification_list:
        cursor.execute("SELECT * FROM Seen WHERE ID_Notification = ?", i['ID_Notification'])
        if cursor.fetchone():
            i['Seen'] = 'True'
        else:
            i['Seen'] = 'False'
            
    print(f"Trả về list các cảnh báo của User {ten_tai_khoan_email_sdt}...")
    cursor.close()
    conn.close()
    return json.dumps(notification_list), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/delete', methods=['POST'])
def delete_notification():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    id_notification = data.get('id_notification ')
    print("id_notification :", id_notification , ' - ', type(id_notification ))

    cursor.execute("SELECT ImagePath FROM Notification WHERE ID_Notification = ?", id_notification)
    row = cursor.fetchone()

    if row:
        image_path = row.ImagePath
        print(f"Đường dẫn của ảnh: {image_path}")

        # Xóa ảnh
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"Đã xóa ảnh có đường dẫn: {image_path}")
        else:
            print(f"Không tìm thấy ảnh có đường dẫn: {image_path}")

        # Xóa hàng dữ liệu trong bảng Notification
        cursor.execute("DELETE FROM Notification WHERE ID_Notification = ?", id_notification)
        conn.commit()
        
        msg = f"Đã xóa hàng dữ liệu với ID_Notification {id_notification}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 200

    else:
        msg = f"Không tìm thấy thông báo với ID_Notification {id_notification}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/get-img', methods=['POST'])
def get_img():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    id_notification = data.get('id_notification')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    print("id_notification:", id_notification, ' - ', type(id_notification))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        # cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        # username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    #----------------------------------------------------------------------
    # Đánh dấu là đã đọc
    cursor.execute("SELECT * FROM Seen WHERE ID_Notification = ? AND CustomerID = ?", (id_notification, customerid))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO Seen (ID_Notification, CustomerID) VALUES (?,?)", (id_notification, customerid))
        # cursor.execute("UPDATE Notification SET Seen = ? WHERE ID_Notification = ?", ('seen', id_notification))
        conn.commit()
    #----------------------------------------------------------------------    
    # try:
    # Lấy ảnh trong từ path và chuyển thành base64
    cursor.execute("SELECT ImagePath FROM Notification WHERE ID_Notification = ?", id_notification)
    row = cursor.fetchone()
    if row:
        image_path = row.ImagePath
        # Chuyển ảnh sang base64
        img = cv2.imread(image_path)
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        _, image_data = cv2.imencode('.jpg', img)
        base64_image = base64.b64encode(image_data).decode("utf-8")
        # Trả về chuỗi base64 cho app
        print("Vừa trả về chuỗi base64")
        cursor.close()
        conn.close()
        return Response(base64_image, mimetype='text/plain')
    else:
        msg = "Thông báo này không có ảnh"
        print(msg)
        cursor.close()
        conn.close()
        return Response(msg, mimetype='text/plain')
    #----------------------------------------------------------------------
    
    # except:
    #     msg = f"Lỗi! Không tìm thấy thông báo có ID {id_notification}"
    #     print(msg)
    #     return Response(msg, mimetype='text/plain')

#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/turn-off', methods=['POST'])
def turn_off_notification():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    camera_id = data.get('camera_id')
    minutes = data.get('minutes')
    
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("camera_id:", camera_id, ' - ', type(camera_id))
    print("minutes:", minutes, ' - ', type(minutes))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
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
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404

    offntfuntil_datetime = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    
    cursor.execute("INSERT INTO OffNotification (CameraID, CustomerID, TimeToTurnOn) VALUES (?, ?, ?)", 
                        (camera_id, customer_id, offntfuntil_datetime))
    conn.commit()
        
    msg = f"Tắt thông báo của User {ten_tai_khoan_email_sdt} về camera {camera_id} cho tới {offntfuntil_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 201

#---------------------------------------------------------------------------------------------------
# CHƯA TEST
@app.route('/api/notification/send-to-user', methods=['POST'])
def send_to_user():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400

    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    ntf_type = data.get('type')
    title = data.get('title')
    body = data.get('body')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("ntf_type:", ntf_type, ' - ', type(ntf_type))
    print("title:", title, ' - ', type(title))
    print("body:", body, ' - ', type(body))

    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    current_time = datetime.datetime.now()
    
    cursor.execute("INSERT INTO Notification (CustomerID, Type, Title, Body, Date) VALUES (?, ?, ?, ?, ?)",
                   (customerid, ntf_type, title, body, current_time))
    conn.commit()
    msg = f"Đã post thông báo cho user {username} lên database"
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 201
#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/get-all', methods=['POST'])
def get_all_notifications():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400

    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    date_range = data.get('date_range')
    print("date_range:", date_range, ' - ', type(date_range))


    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        # cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        # username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    # Lấy ID nhà
    cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ?", (customerid,))
    home_ids = [row.HomeID for row in cursor.fetchall()]
    # Lấy ID nhà được thêm quyền
    cursor.execute("SELECT HomeID FROM HomeMember WHERE HomeMemberID = ?", (customerid,))
    home_ids = home_ids + [row.HomeID for row in cursor.fetchall()]

    # Lặp qua từng HomeID và lấy danh sách CameraID từ đó (lấy tất cả CameraID mà User có quyền truy cập)
    camera_ids = []
    for home_id in home_ids:
        cursor.execute("SELECT CameraID FROM Camera WHERE HomeID = ?", (home_id,))
        camera_ids.extend([row.CameraID for row in cursor.fetchall()])
        
    # try:
    # cursor.execute(f"SELECT * FROM Notification WHERE CameraID IN ({params}) ORDER BY Date DESC", camera_id)
    """
        Biết mỗi hàng trong bảng Notification nếu cột CameraID có giá trị thì cột CustomerID là Null và ngược lại, 
        Lấy ra các hàng có CameraID nằm trong list camera_ids, 
            hoặc có CustomerID = customerid, 
        Với các hàng có CameraID nằm trong list camera_ids thì phải lấy ra CameraName, 
            nếu không thì trả về CameraName là null
    """
    cursor.execute(f"""
                        SELECT
                            CASE
                                WHEN C.CameraID IN ({', '.join(map(str, camera_ids))}) THEN C.CameraName
                                ELSE NULL
                            END AS CameraName,
                            N.*
                        FROM
                            Notification N
                        LEFT JOIN
                            Camera C ON N.CameraID = C.CameraID
                        WHERE
                            N.CameraID IN ({', '.join(map(str, camera_ids))}) OR N.CustomerID = {customerid}
                        ORDER BY N.Date DESC
                    """)
    notifications = cursor.fetchall()
    notification_list = []
    if date_range is not None:
        date_parts = date_range.split(" - ")
        start_date = datetime.datetime.strptime(date_parts[0], "%Y-%m-%d %H:%M:%S.%f")
        end_date = datetime.datetime.strptime(date_parts[1], "%Y-%m-%d %H:%M:%S.%f")
        
    for notification in notifications:
        if date_range is not None:
            date = notification.Date
            if start_date <= date <= (end_date+datetime.timedelta(days=1)):
                notification_list.append({
                    'CameraID': notification.CameraID,
                    'CameraName': notification.CameraName,
                    'ID_Notification': notification.ID_Notification,
                    'Type': notification.Type,
                    'Title': notification.Title,
                    'Body': notification.Body,
                    'Date': notification.Date.strftime("%d-%m-%Y %Hh%M'%S\""),
                })
        else:
            notification_list.append({
                'CameraID': notification.CameraID,
                'CameraName': notification.CameraName,
                'ID_Notification': notification.ID_Notification,
                'Type': notification.Type,
                'Title': notification.Title,
                'Body': notification.Body,
                'Date': notification.Date.strftime("%d-%m-%Y %Hh%M'%S\""),
            })
        
    for i in notification_list:
        # Trả về trường "Seen" để biết thông báo đã xem chưa
        cursor.execute("SELECT * FROM Seen WHERE ID_Notification = ?", i['ID_Notification'])
        if cursor.fetchone():
            i['Seen'] = 'True'
        else:
            i['Seen'] = 'False'
        # Trả về hình ảnh của thông báo nếu có
        
            
    print(f"Trả về list các thông báo của User {ten_tai_khoan_email_sdt}...")
    cursor.close()
    conn.close()
    return json.dumps(notification_list), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/set-seen', methods=['POST'])
def set_seen():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    id_notification = data.get('id_notification')
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    print("id_notification:", id_notification, ' - ', type(id_notification))
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        # cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        # username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    cursor.execute("SELECT * FROM Seen WHERE ID_Notification = ? AND CustomerID = ?", (id_notification, customerid))
    if cursor.fetchone():
        cursor.execute("INSERT INTO Seen (ID_Notification, CustomerID) VALUES (?,?)", (id_notification, customerid))
        # cursor.execute("UPDATE Notification SET Seen = ? WHERE ID_Notification = ?", ('seen', id_notification))
        conn.commit()
    msg = f"Đã set seen thông báo có ID {id_notification}"
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/set-all-seen', methods=['POST'])
def set_all_seen():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        # cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        # username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404

    # Lấy ID nhà
    cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ?", (customerid,))
    home_ids = [row.HomeID for row in cursor.fetchall()]
    # Lấy ID nhà được thêm quyền
    cursor.execute("SELECT HomeID FROM HomeMember WHERE HomeMemberID = ?", (customerid,))
    home_ids = home_ids + [row.HomeID for row in cursor.fetchall()]

    # Lặp qua từng HomeID và lấy danh sách CameraID từ đó
    camera_ids = []
    for home_id in home_ids:
        cursor.execute("SELECT CameraID FROM Camera WHERE HomeID = ?", (home_id,))
        camera_ids.extend([row.CameraID for row in cursor.fetchall()])
        
    # try:
    # cursor.execute(f"SELECT * FROM Notification WHERE CameraID IN ({params}) ORDER BY Date DESC", camera_id)
    """
        Biết mỗi hàng trong bảng Notification nếu cột CameraID có giá trị thì cột CustomerID là Null và ngược lại, 
        Lấy ra các hàng có CameraID nằm trong list camera_ids, 
            hoặc có CustomerID = customerid, 
        Với các hàng có CameraID nằm trong list camera_ids thì phải lấy ra CameraName, 
            nếu không thì trả về CameraName là null
    """
    cursor.execute(f"""
                        SELECT
                            N.ID_Notification
                        FROM
                            Notification N
                        LEFT JOIN
                            Camera C ON N.CameraID = C.CameraID
                        WHERE
                            N.CameraID IN ({', '.join(map(str, camera_ids))}) OR N.CustomerID = {customerid}
                        ORDER BY N.Date DESC
                    """)
    results = cursor.fetchall()
    
    cursor.execute("DELETE FROM Seen WHERE CustomerID = ?", (customerid,))
    conn.commit()
    for result in results:
        cursor.execute("INSERT INTO Seen (ID_Notification, CustomerID) VALUES (?, ?)", (result.ID_Notification, customerid))
    conn.commit()
    msg = f"Đã set seen tất cả thông báo của User {ten_tai_khoan_email_sdt}"
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/count-new', methods=['POST'])
def count_new_ntf():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400

    ten_tai_khoan_email_sdt = data.get('ten_tai_khoan_email_sdt')
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))


    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        customerid = cursor.fetchone().CustomerID
        # cursor.execute("SELECT Username FROM Customer WHERE CustomerID = ?", customerid)
        # username = cursor.fetchone().Username
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    # Lấy ID nhà
    cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ?", (customerid,))
    home_ids = [row.HomeID for row in cursor.fetchall()]
    # Lấy ID nhà được thêm quyền
    cursor.execute("SELECT HomeID FROM HomeMember WHERE HomeMemberID = ?", (customerid,))
    home_ids = home_ids + [row.HomeID for row in cursor.fetchall()]

    # Lặp qua từng HomeID và lấy danh sách CameraID từ đó (lấy tất cả CameraID mà User có quyền truy cập)
    camera_ids = []
    for home_id in home_ids:
        cursor.execute("SELECT CameraID FROM Camera WHERE HomeID = ?", (home_id,))
        camera_ids.extend([row.CameraID for row in cursor.fetchall()])
    
    if len(camera_ids)==0:
        cursor.execute("SELECT COUNT(*) FROM Notification WHERE CustomerID = ?", (customerid,))
    else:
        cursor.execute("""
                            SELECT COUNT(*)
                            FROM Notification
                            WHERE CameraID IN ({camera_ids}) OR CustomerID = {customerid}
                        """.format(camera_ids=', '.join(map(str, camera_ids)), customerid=customerid))
        
    all_ntf = cursor.fetchone()[0]
    cursor.execute(f"""SELECT COUNT(*) FROM Seen 
                        WHERE CustomerID = {customerid}
                    """)
    count = all_ntf - cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return jsonify({"message": count}), 200
    # return Response(str(count), mimetype='text/plain'), 200
#########################################################################################################################
#########################################################################################################################

#-------------------------------------API cho Python-------------------------------------  
  
@app.route('/api/notification/get-camera-id', methods=['POST'])
def get_camera_id():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    rtsp = data.get('rtsp')
    print("rtsp:", rtsp, ' - ', type(rtsp))
    cursor.execute("SELECT CameraID, RTSP_encode FROM Camera")
    results = cursor.fetchall()
    for result in results:
        if rtsp == aes_decrypt(result.RTSP_encode):     
            msg = f"Trả về id camera có rtsp là {rtsp}"
            print(msg)
            cursor.close()
            conn.close()
            return jsonify({'message': result.CameraID}), 200
#---------------------------------------------------------------------------------------------------

@app.route('/api/camera/info', methods=['POST'])
def camera_info():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    camera_id = data.get('camera_id')
    print("camera_id:", camera_id, ' - ', type(camera_id))
    
    cursor.execute("SELECT * FROM Camera WHERE CameraID=?", (camera_id,))
    
    cam = cursor.fetchone()
    rtsp = aes_decrypt(cam.RTSP_encode)
    cam_username = rtsp.split(":")[1][2:]
    cam_pass = '@'.join(rtsp.split(":")[2].split("@")[:-1])
    ddns = rtsp.split("@")[-1].split(":")[0]
    port = rtsp.split(":")[-1].split("/")[0]
    
    camera_info_list = []
    camera_info_list.append({
        'camera_name': cam.CameraName,
        'cam_username': cam_username,
        'cam_pass': cam_pass,
        'ddns': ddns,
        'port': port,
    })
    print(f"Trả về danh sách thông tin camera")
    cursor.close()
    conn.close()
    return json.dumps(camera_info_list), 200

#---------------------------------------------------------------------------------------------------  
  
@app.route('/api/notification/save', methods=['POST'])
def save_notification():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    notification_type = data.get('notification_type')
    title = data.get('title')
    body = data.get('body')
    anh_base64 = data.get('base64')
    camera_id = data.get('camera_id')
    formatted_time = data.get('formatted_time')
    
    print("notification_type:", notification_type, ' - ', type(notification_type))
    print("title:", title, ' - ', type(title))
    print("body:", body, ' - ', type(body))
    print("camera_id:", camera_id, ' - ', type(camera_id))

    # Lấy thông tin ngày, tạo tên ảnh
    current_time = datetime.datetime.strptime(formatted_time, "%d-%m-%Y %Hh%M'%S\"")
    time_string = current_time.strftime("%H%M%S_%d%m%Y")
    folder_path = f"Notification/{camera_id}/"
    img_path = folder_path + f"{time_string}.jpg" ##### <<<<<<<<<<<<<<<<<<<<<<<<<<<
    
    # Kiểm tra thư mục ảnh thông báo tồn tại chưa
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # Chuyển base64 sang ảnh
    anh_base64 = np.frombuffer(base64.b64decode(anh_base64), dtype=np.uint8)
    anh_base64 = cv2.imdecode(anh_base64, cv2.IMREAD_ANYCOLOR)
    # image_rgb = cv2.cvtColor(anh_base64, cv2.COLOR_BGR2RGB)
    
    # Lưu ảnh vào folder "Notification/{camera_id}/"
    cv2.imwrite(img_path, anh_base64)
    
    #----------------------------------------------------------------------------------------------
    
    # try:
    cursor.execute("INSERT INTO Notification (CameraID, Type, Title, Body, Date, ImagePath) VALUES (?, ?, ?, ?, ?, ?)", 
                   (camera_id, notification_type, title, body, current_time, img_path))
    conn.commit()
    
    msg = f"Đã lưu thông tin về thông báo vào database"
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 201

    # except:
    #     msg = f"Lỗi! Không cập nhật được thông báo"
    #     print(msg)
    #     return jsonify({'message': msg}), 404

#---------------------------------------------------------------------------------------------------

@app.route('/api/notification/get-fcm-to-send', methods=['POST'])
def get_fcm_to_send():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    # OffNotification (CameraID, CustomerID, TimeToTurnOn)
    camera_id = data.get('camera_id')
    print("camera_id:", camera_id, ' - ', type(camera_id))

    cursor.execute("SELECT * FROM OffNotification WHERE CameraID = ?", (camera_id,))
    rows = cursor.fetchall()

    # Duyệt qua các hàng, xóa hàng đó nếu đã hết tgian tắt thông báo
    current_datetime = datetime.datetime.now()
    for row in rows:
        timetoturnon = row.TimeToTurnOn
        # Nếu đã hết thời gian tắt thông báo
        if current_datetime > timetoturnon:
            cursor.execute("DELETE FROM OffNotification WHERE CameraID = ? AND CustomerID = ?", 
                           (camera_id, row.CustomerID))
            conn.commit()
    
    # Lấy danh sách quyền từ camera_id
    cursor.execute(f"""
                        SELECT hm.AdminID, hm.HomeMemberID
                        FROM HomeMember hm
                        INNER JOIN Camera cam ON hm.HomeID = cam.HomeID
                        WHERE cam.CameraID = {camera_id};
                    """)
    rows = cursor.fetchall()
    customer_ids = []

    for row in rows:
        customer_ids.append(row.AdminID)
        customer_ids.append(row.HomeMemberID)
        
    # Lấy ID Admin nếu căn hộ k có member
    cursor.execute(f"""
                        SELECT ch.CustomerID
                        FROM Camera c
                        INNER JOIN CustomerHome ch ON c.HomeID = ch.HomeID
                        WHERE c.CameraID = {camera_id}
                    """)
    row = cursor.fetchone()
    fcm_list = []
    if row is None:
        print(f"Không tìm thấy camera có ID là {camera_id}")
        cursor.close()
        conn.close()
        return json.dumps(fcm_list), 200
    customer_ids.append(row.CustomerID)
    
    customer_ids = list(set(customer_ids))
    
    cursor.execute("SELECT * FROM OffNotification WHERE CameraID = ?", (camera_id,))
    off_customer_ids = [row.CustomerID for row in cursor.fetchall()]

    on_customer_ids = [customer_id for customer_id in customer_ids if customer_id not in off_customer_ids]
    
    # Lấy danh sách FCM
    cursor.execute("SELECT FCM FROM CustomerDevice WHERE CustomerID IN ({})".format(', '.join(map(str, on_customer_ids))))
    fcm_list = [row.FCM for row in cursor]
    
    print(f"Trả về danh sách FCM của các User có quyền coi camera {camera_id}")
    cursor.close()
    conn.close()
    return json.dumps(fcm_list), 200
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/pose/get-camera-data', methods=['POST'])
def get_camera_data():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    # Truy vấn SQL để lấy dữ liệu từ bảng Camera
    cursor.execute("SELECT CameraID, HomeID, LockID, CameraName, RTSP_encode, LockpickingArea, ClimbingArea, BikeArea, RelatedCameraID FROM Camera")
    
    # Trích xuất dữ liệu từ kết quả truy vấn
    camera_data = []
    for row in cursor.fetchall():
        # Thêm dữ liệu vào danh sách camera_data
        camera_data.append({
            'CameraID': row.CameraID,
            'HomeID': row.HomeID,
            'LockID': row.LockID,
            'CameraName': row.CameraName,
            'RTSP': aes_decrypt(row.RTSP_encode),
            'LockpickingArea': json.loads(row.LockpickingArea) if row.LockpickingArea else None,
            'ClimbingArea': json.loads(row.ClimbingArea) if row.ClimbingArea else None,
            'BikeArea': json.loads(row.BikeArea) if row.BikeArea else None,
            'RelatedCameraID': row.RelatedCameraID,
        })
    print(f"Trả về thông tin tất cả Camera")
    cursor.close()
    conn.close()
    return json.dumps(camera_data), 200
    
#---------------------------------------------------------------------------------------------------

#########################################################################################################################
#########################################################################################################################

#------------------------------------------------- API liên quan tới FaceID ---------------------------------------------

@app.route('/api/faceid/upload-image', methods=['POST'])
def faceid_upload_image():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.form
    key = data['key']
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400

    if 'image' not in request.files:
        print("Chưa truyền file ảnh")
        cursor.close()
        conn.close()
        return jsonify({"message": "Chưa truyền file ảnh"}), 400

    face_name = data['face_name']
    
    ten_tai_khoan_email_sdt = data['ten_tai_khoan_email_sdt']
    homename = data['homename']
    
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    print("homename:", homename, ' - ', type(homename))
    
    #---------------------------------------- Lấy ra homeid -------------------------------------------
    # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
    try:
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        results = cursor.fetchall()
        customer_id = results[0][0]
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    # Từ CustomerID lấy HomeID trong bảng CustomerHome
    try:
        cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ? AND HomeName = ?", (customer_id, homename))
        results = cursor.fetchall()
        homeid = results[0][0]
    except:
        msg = f"User {ten_tai_khoan_email_sdt} không phải chủ của căn hộ"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    file = request.files['image']
        
    # Lưu ảnh nhận được từ request vào máy chạy API
    if not os.path.exists('hinhanh'):
        os.makedirs('hinhanh')
    save_path = 'hinhanh/lastest_upload.jpg'
    file.save(save_path)
    
    #---------------------------------------- Lấy ảnh khuôn mặt base64 --------------------------------------------
    
    if not os.path.exists('hinhtrain'):
        os.makedirs('hinhtrain')
    pixels = pyplot.imread(save_path)
    base_img = pixels.copy()
    h = base_img.shape[0]
    w = base_img.shape[1]
    original_size = base_img.shape
    target_size = (300, 300)
    img = cv2.resize(pixels, target_size)
    aspect_ratio_x = (original_size[1] / target_size[1])
    aspect_ratio_y = (original_size[0] / target_size[0])
    imageBlob = cv2.dnn.blobFromImage(img, 1.0, (300, 300), (104.0, 177.0, 123.0))
    detectorssd.setInput(imageBlob)
    detections = detectorssd.forward()
    column_labels = ["img_id", "is_face", "confidence", "left", "top", "right", "bottom"]
    detections_df = pd.DataFrame(detections[0][0], columns = column_labels)

    detections_df = detections_df[detections_df['is_face'] == 1]
    detections_df = detections_df[detections_df['confidence'] >= 0.5]
    
    if detections_df.empty:
        msg = "Không tìm thấy khuôn mặt trong ảnh"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({"message": msg}), 400
    
    detections_df['left'] = (detections_df['left'] * 300).astype(int)
    detections_df['bottom'] = (detections_df['bottom'] * 300).astype(int)
    detections_df['right'] = (detections_df['right'] * 300).astype(int)
    detections_df['top'] = (detections_df['top'] * 300).astype(int)
    # Tìm chỉ số của dòng có confidence lớn nhất
    max_confidence_idx = detections_df['confidence'].idxmax()
    # Trích xuất dòng có confidence lớn nhất
    max_confidence_instance = detections_df.loc[max_confidence_idx]
    left = max_confidence_instance["left"]; right = max_confidence_instance["right"]
    bottom = max_confidence_instance["bottom"]; top = max_confidence_instance["top"]
    if top < 0: top = 0
    if left < 0: left = 0
    if bottom > h: bottom = h
    if right > w: right = w

    crop_img = base_img[int(top * aspect_ratio_y):int(bottom * aspect_ratio_y),
                        int(left * aspect_ratio_x):int(right * aspect_ratio_x)]
    crop_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
    crop_img = padding_face(crop_img, target_size=(224, 224))
    
    crop_path = 'hinhtrain/lastest_upload.jpg'
    if os.path.exists(crop_path):
        os.remove(crop_path)
    cv2.imwrite(crop_path, crop_img)

    _, image_data = cv2.imencode('.jpg', crop_img)
    
    # Chuyển đổi dữ liệu ảnh thành chuỗi base64
    base64_image = base64.b64encode(image_data).decode("utf-8")
    
    #------------------------------------------ Up ảnh lên database -------------------------------------------
    
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d_%Hh%Mm%Ss")
    file_name = f"{formatted_time}.jpg"
    upload_folder = 'hinhtrain'
    # Kiểm tra (face_name, homeid) có trong bảng Face chưa, nếu chưa INSERT vào
    cursor.execute("SELECT FaceID FROM FaceRegData WHERE FaceName = ? AND HomeID = ?",
                   (face_name, homeid))
    row = cursor.fetchone()
    if row:
        print(f'{face_name} ĐÃ CÓ ảnh trong csdl, bắt đầu thêm ảnh...')
        face_id = row.FaceID
    else:
        print(f'{face_name} CHƯA CÓ ảnh trong csdl, bắt đầu thêm ảnh...')
        cursor.execute("SELECT MAX(FaceID) FROM FaceRegData")
        max_face_id = cursor.fetchone()[0]
        face_id = (max_face_id + 1) if max_face_id!=None else 1
        
    image_path = os.path.join(upload_folder, str(homeid), str(face_id), file_name).replace("\\", "/")
    cursor.execute("""INSERT INTO FaceRegData (FaceID, FaceName, HomeID, ImagePath, Base64) 
                    VALUES (?, ?, ?, ?, ?)""",
                (face_id, face_name, homeid, image_path, base64_image))
    conn.commit()
    msg = f"Thêm ảnh thành công"
    print(msg)
    cursor.close()
    conn.close()
    return jsonify({'message': msg}), 201

#---------------------------------------------------------------------------------------------------

@app.route('/api/home/get-facename', methods=['POST'])
def get_facename_in_home():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    ten_tai_khoan_email_sdt = data['ten_tai_khoan_email_sdt']
    print("ten_tai_khoan_email_sdt:", ten_tai_khoan_email_sdt, ' - ', type(ten_tai_khoan_email_sdt))
    
    #---------------------------------------- Lấy ra customer_id -------------------------------------------
    try:
        # Từ "ten_tai_khoan_email_sdt" lấy CustomerID trong bảng Customer
        if "@" in ten_tai_khoan_email_sdt:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Email = ?", ten_tai_khoan_email_sdt)
        elif ten_tai_khoan_email_sdt.isdigit():
            cursor.execute("SELECT CustomerID FROM Customer WHERE Mobile = ?", ten_tai_khoan_email_sdt)
        else:
            cursor.execute("SELECT CustomerID FROM Customer WHERE Username = ?", ten_tai_khoan_email_sdt)
            
        results = cursor.fetchall()
        customer_id = results[0][0]
    except:
        msg = f"Lỗi! Không lấy được Username của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    # Từ CustomerID lấy danh sách HomeID của người đó trong bảng CustomerHome (k tính camera được thêm quyền)
    try:
        cursor.execute("SELECT HomeID FROM CustomerHome WHERE CustomerID = ?", (customer_id,))
        homeid_list = [row[0] for row in cursor.fetchall()]
    except:
        msg = f"Lỗi! Không lấy được homeid của User {ten_tai_khoan_email_sdt}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 404
    
    facename_list = []
    if len(homeid_list)>0:
        # Lấy ra danh sách những khuôn mặt được thêm vào dữ liệu nhận diện của các căn trong "homeid_list"
        cursor.execute("""
                        SELECT DISTINCT FaceID, FaceName, HomeID
                        FROM FaceRegData 
                        WHERE HomeID IN ({}) 
                        ORDER BY HomeID
                    """.format(', '.join(map(str, homeid_list)))
                    )
        rows = cursor.fetchall()
        
        for row in rows:
            # Tính số lượng ảnh của mỗi người đã thêm vào dữ liệu nhận diện
            cursor.execute("SELECT COUNT(*) FROM FaceRegData WHERE FaceID = ?", (row.FaceID,))
            number_of_images = cursor.fetchone()[0]
            
            cursor.execute("SELECT HomeName FROM CustomerHome WHERE HomeID = ?", (row.HomeID,))
            homename = cursor.fetchone()[0]
            
            facename_list.append({
                'FaceID': str(row.FaceID),
                'FaceName': row.FaceName,
                'NumberOfImage': number_of_images, # Trả về số lượng ảnh đã thêm của người đó
                'HomeName': homename,
            })
    
    print(f"Trả về danh sách tên các khuôn mặt được User {ten_tai_khoan_email_sdt} thêm vào dữ liệu nhận diện")
    cursor.close()
    conn.close()
    return json.dumps(facename_list), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/faceid/get-image', methods=['POST'])
def get_images_by_faceid():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    faceid = int(data.get('faceid'))
    print("faceid:", faceid, ' - ', type(faceid))
    
    cursor.execute("SELECT ImageID, Base64 FROM FaceRegData WHERE FaceID = ?", (faceid,))
    rows = cursor.fetchall()
    image_list = []
    for row in rows:
        image_list.append({
            'ImageID': row.ImageID,
            'Base64': row.Base64,
        })
    
    print(f"Trả về danh sách các hình ảnh cho FaceID {faceid}")
    cursor.close()
    conn.close()
    return json.dumps(image_list), 200

#---------------------------------------------------------------------------------------------------

@app.route('/api/faceid/delete-face-img', methods=['POST'])
def delete_face_img():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    image_id = int(data.get('image_id'))
    print("image_id:", image_id, ' - ', type(image_id))

    try:
        cursor.execute("DELETE FROM FaceRegData WHERE ImageID = ?", (image_id,))
        conn.commit()
        msg = f"Đã xóa ảnh"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 200
    except Exception as e:
        msg = f"Không xóa được ảnh"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    
#---------------------------------------------------------------------------------------------------

@app.route('/api/faceid/delete-face', methods=['POST'])
def delete_face():
    conn = connect_to_database()
    cursor = conn.cursor()
    data = request.get_json()
    key = data.get('key')
    if key not in api_keys:
        print('Sai key')
        cursor.close()
        conn.close()
        return jsonify({'message': 'Sai key'}), 400
    
    faceid = int(data.get('faceid'))
    print("faceid:", faceid, ' - ', type(faceid))

    try:
        cursor.execute("DELETE FROM FaceRegData WHERE FaceID = ?", (faceid,))
        conn.commit()
        msg = f"Đã xóa Face có ID là {faceid}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 200
    except Exception as e:
        msg = f"Không xóa được Face có ID là {faceid}"
        print(msg)
        cursor.close()
        conn.close()
        return jsonify({'message': msg}), 500
    
#########################################################################################################################
#########################################################################################################################
if __name__ == '__main__':
    while True:
        try:
            app.run(host=ip_address, port=5001)
        except pyodbc.OperationalError:
            conn = connect_to_database()
            cursor = conn.cursor()
            pass
