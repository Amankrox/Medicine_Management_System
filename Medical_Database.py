import json
import tornado.ioloop
import tornado.web
from pymongo import MongoClient
from bson import ObjectId
import bcrypt
import csv
import re
import datetime
import logging
import xlsxwriter
from datetime import datetime, timedelta

client = MongoClient('mongodb://localhost:27017/')
db = client['user_db']
users_collection = db['users']
categories_collection = db['categories']
pharmacies_collection = db['pharmacies']
medicines_collection = db['medicines']
sales_collection = db['sales']

user_id = 0;

# Authentication decorator
def requires_auth(method):
    def wrapper(self, *args, **kwargs):
        token = self.request.headers.get('Authorization')
        user = users_collection.find_one({'token': token})
        if not user:
            self.set_status(401)
            self.write("Unauthorized")
        else:
            return method(self, *args, **kwargs)
    return wrapper

# For registration
class RegisterHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body)
            password = data.get('password')
            name = data.get('name')
            mobile_number = data.get('mobile_number')
            age = data.get('age')
            email = data.get('email')

            if not password or not name or not mobile_number or not age or not email:
                raise ValueError("All fields are required")

            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                raise ValueError("Invalid email format")

            hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

            user = {
                'password': hashed_password,
                'name': name,
                'mobile_number': mobile_number,
                'age': age,
                'email': email
            }

            existing_user = users_collection.find_one({'email': email})
            if existing_user:
                raise ValueError("Email already exists")

            users_collection.insert_one(user)
            self.write("User registered successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

# For handling login
class LoginHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body)
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                raise ValueError("Username or password missing")

            user = users_collection.find_one({'email': email})
            global user_id
            user_id = user["_id"]
            if user and bcrypt.checkpw(password.encode(), user['password']):
                token = bcrypt.gensalt()
                users_collection.update_one({'email': email}, {'$set': {'token': token}})
                self.set_header('Authorization', token.decode())
                self.write("Login successful.")
            else:
                self.write("Invalid username/email or password.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

# For creating, editing, and removing pharmacies
class PharmacyHandler(tornado.web.RequestHandler):
    @requires_auth
    def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body)
            pharmacy_name = data.get('name')
            pharmacy_location = data.get('location')

            if not pharmacy_name or not pharmacy_location or not user_id:
                raise ValueError("Pharmacy name, location, and user_id are required")

            # Check if the user_id exists
            if not users_collection.find_one({'_id': user_id}):
                raise ValueError("User does not exist")

            # Check if the user is logged in
            token = self.request.headers.get('Authorization')
            user = users_collection.find_one({'token': token})
            if not user:
                raise ValueError("User is not logged in")

            pharmacy = {
                'name': pharmacy_name,
                'location': pharmacy_location,
                'user_id': user_id
            }
            pharmacies_collection.insert_one(pharmacy)
            self.write("Pharmacy added successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

    @requires_auth
    def put(self, pharmacy_id):
        try:
            data = tornado.escape.json_decode(self.request.body)
            pharmacy_name = data.get('name')
            pharmacy_location = data.get('location')
            user_id = data.get('user_id')

            if not pharmacy_name or not pharmacy_location or not user_id:
                raise ValueError("Pharmacy name, location, and user_id are required")

            # Check if the user_id exists
            if not users_collection.find_one({'_id': ObjectId(user_id)}):
                raise ValueError("User does not exist")

            # Check if the user is logged in
            token = self.request.headers.get('Authorization')
            user = users_collection.find_one({'token': token})
            if not user:
                raise ValueError("User is not logged in")
            # Convert pharmacy_id to ObjectId
            pharmacy_id_obj = ObjectId(pharmacy_id)

            pharmacies_collection.update_one({'_id': pharmacy_id_obj}, {'$set': {'name': pharmacy_name, 'location': pharmacy_location, 'user_id': user_id}})
            self.write("Pharmacy updated successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

    @requires_auth
    def delete(self, pharmacy_id):
        try:
            # Check if the user is logged in
            token = self.request.headers.get('Authorization')
            user = users_collection.find_one({'token': token})
            if not user:
                raise ValueError("User is not logged in")
            # Convert pharmacy_id to ObjectId
            pharmacy_id_obj = ObjectId(pharmacy_id)

            pharmacies_collection.delete_one({'_id': pharmacy_id_obj})
            self.write("Pharmacy deleted successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

# For creating, editing, and removing categories
class CategoryHandler(tornado.web.RequestHandler):
    @requires_auth
    def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body)
            category_name = data.get('name')

            if not category_name:
                raise ValueError("Category name missing")

            category = {
                'name': category_name
            }
            categories_collection.insert_one(category)
            self.write("Category added successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

    @requires_auth
    def put(self, category_id):
        try:
            data = tornado.escape.json_decode(self.request.body)
            category_name = data.get('name')

            if not category_name:
                raise ValueError("Category name missing")

            categories_collection.update_one({'_id': ObjectId(category_id)}, {'$set': {'name': category_name}})
            self.write("Category updated successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

    @requires_auth
    def delete(self, category_id):
        try:
            categories_collection.delete_one({'_id': ObjectId(category_id)})
            self.write("Category deleted successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

# For adding, updating, and removing categories for a pharmacy
class PharmacyCategoryHandler(tornado.web.RequestHandler):
    @requires_auth
    def post(self, pharmacy_id):
        try:
            data = tornado.escape.json_decode(self.request.body)
            category_id = data.get('category_id')

            if not category_id:
                raise ValueError("Category ID missing")

            pharmacies_collection.update_one({'_id': ObjectId(pharmacy_id)}, {'$addToSet': {'categories': category_id}})
            self.write("Category added to pharmacy successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

    @requires_auth
    def put(self, pharmacy_id, category_id):
        try:
            data = tornado.escape.json_decode(self.request.body)
            new_category_id = data.get('new_category_id')

            if not new_category_id:
                raise ValueError("New Category ID missing")

            pharmacies_collection.update_one({'_id': ObjectId(pharmacy_id), 'categories': ObjectId(category_id)}, {'$set': {'categories.$': ObjectId(new_category_id)}})
            self.write("Category updated for pharmacy successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

    @requires_auth
    def delete(self, pharmacy_id, category_id):
        try:
            pharmacies_collection.update_one({'_id': ObjectId(pharmacy_id)}, {'$pull': {'categories': category_id}})
            self.write("Category removed from pharmacy successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

# For creating, editing, and removing stock of medicines
class MedicineHandler(tornado.web.RequestHandler):
    @requires_auth
    def post(self, medicine_id=None):
        try:
            data = tornado.escape.json_decode(self.request.body)
            action = data.get('action')

            if action == 'create':
                # Medicine creation logic
                name = data.get('name')
                description = data.get('description')
                price = data.get('price')
                stock_quantity = data.get('stock_quantity')
                category_id = data.get('category_id')

                if not name or not description or not price or not stock_quantity or not category_id:
                    raise ValueError("Missing required fields")

                medicine = {
                    'name': name,
                    'description': description,
                    'price': price,
                    'stock_quantity': stock_quantity,
                    'category_id': category_id
                }
                medicines_collection.insert_one(medicine)
                self.write("Medicine added successfully.")

            elif action == 'update':
                # Medicine update logic
                if not medicine_id:
                    raise ValueError("Medicine ID is required for update")

                update_data = {}
                if 'name' in data:
                    update_data['name'] = data['name']
                if 'description' in data:
                    update_data['description'] = data['description']
                if 'price' in data:
                    update_data['price'] = data['price']
                if 'stock_quantity' in data:
                    update_data['stock_quantity'] = data['stock_quantity']
                if 'category_id' in data:
                    update_data['category_id'] = data['category_id']

                if not update_data:
                    raise ValueError("No update fields provided")

                medicines_collection.update_one({'_id': ObjectId(medicine_id)}, {'$set': update_data})
                self.write("Medicine updated successfully.")

            elif action == 'delete':
                # Medicine delete logic
                if not medicine_id:
                    raise ValueError("Medicine ID is required for delete")

                medicines_collection.delete_one({'_id': ObjectId(medicine_id)})
                self.write("Medicine deleted successfully.")

            else:
                raise ValueError("Invalid action")

        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))
# #COustom JSON encoder to handle date nad time 
# class CustomJSONEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, datetime.date):
#             return obj.isoformat()
#         return super().default(obj)            


# For creating, editing, and removing sales
class SalesHandler(tornado.web.RequestHandler):
    @requires_auth
    def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body)
            medicine_id = data.get('medicine_id')
            no_of_units_sold = data.get('no_of_units_sold')
            total_price = data.get('total_price')
            # print("this is medicine id ", medicine_id)

            if not medicine_id or not no_of_units_sold or not total_price:
                raise ValueError("Missing required fields")

            # Update medicine table
            medicine = medicines_collection.find_one({'_id': ObjectId(medicine_id)})
            print("this is medicine", medicine)
            if not medicine:
                raise ValueError("Medicine not found")
            left_units = int(medicine['stock_quantity']) - int(no_of_units_sold)
            if left_units < 0:
                raise ValueError("Not enough units available in stock")
            medicines_collection.update_one({'_id': ObjectId(medicine_id)}, {'$set': {'stock_quantity': left_units}})

            current_date = datetime.datetime.now().strftime('%Y-%m-%d')
            current_time = datetime.datetime.now().strftime('%H:%M:%S')

            sale = {
                'medicine_id': medicine_id,
                'no_of_units_sold': no_of_units_sold,
                'total_price': total_price,
                'current_date': current_date,
                'current_time': current_time
            }
            # Insert sale
            sales_collection.insert_one(sale)
            self.write("Sale added successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

    @requires_auth
    def put(self, sale_id):
        try:
            data = tornado.escape.json_decode(self.request.body)
            no_of_units_sold = data.get('no_of_units_sold')
            total_price = data.get('total_price')
            current_date = data.get('current_date')
            current_time = data.get('current_time')

            if not no_of_units_sold or not total_price or not current_date or not current_time:
                raise ValueError("Missing required fields")

            sale = sales_collection.find_one({'_id': ObjectId(sale_id)})
            if not sale:
                raise ValueError("Sale not found")

            # Update medicine table
            medicine_id = sale['medicine_id']
            print(medicine_id)
            medicine = medicines_collection.find_one({'_id': ObjectId(medicine_id)})
            if not medicine:
                raise ValueError("Medicine not found")
            total_units = medicine['stock_quantity'] +int(sale['no_of_units_sold']) - int(no_of_units_sold)
            print(total_units)
            if total_units < 0:
                raise ValueError("Not enough units available in stock")
            medicines_collection.update_one({'_id': medicine_id}, {'$set': {'stock_quantity': total_units}})

            # Update sale
            sales_collection.update_one({'_id': ObjectId(sale_id)}, {'$set': {
                'no_of_units_sold': no_of_units_sold,
                'total_price': total_price,
                'current_date': current_date,
                'current_time': current_time
            }})
            self.write("Sale updated successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

    @requires_auth
    def delete(self, sale_id):
        try:
            sale = sales_collection.find_one({'_id': ObjectId(sale_id)})
            if not sale:
                raise ValueError("Sale not found")

            # Update medicine table
            medicine_id = sale['medicine_id']
            medicine = medicines_collection.find_one({'_id': ObjectId(medicine_id)})
            if not medicine:
                raise ValueError("Medicine not found")
            total_units = medicine['stock_quantity'] + sale['no_of_units_sold']
            medicines_collection.update_one({'_id': ObjectId(medicine_id)}, {'$set': {'stock_quantity': total_units}})


              # Delete sale
            sales_collection.delete_one({'_id': ObjectId(sale_id)})
            self.write("Sale deleted successfully.")
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))

    @requires_auth
    def get(self):
        try:
            # Retrieve all sales records
            sales = list(sales_collection.find())

              # Generate Excel sheet
            workbook = xlsxwriter.Workbook('sales_report.xlsx')
            worksheet = workbook.add_worksheet()

            # Write header row
            headers = ['Medicine ID', 'No of Units Sold', 'Total Price', 'Date', 'Time']
            for i, header in enumerate(headers):
                worksheet.write(0, i, header)

            # Write data rows
            for i, sale in enumerate(sales):
                worksheet.write(i + 1, 0, str(sale['medicine_id']))
                worksheet.write(i + 1, 1, sale['no_of_units_sold'])
                worksheet.write(i + 1, 2, sale['total_price'])
                worksheet.write(i + 1, 3, sale['current_date'])
                worksheet.write(i + 1, 4, sale['current_time'])

            workbook.close()

            # Set headers for downloading the file
            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition', 'attachment; filename="sales_report.xlsx"')
            with open('sales_report.xlsx', 'rb') as file:
                self.write(file.read())
        except Exception as e:
            self.set_status(400)
            self.write("Error: {}".format(str(e)))               
def make_app():
    return tornado.web.Application([
        (r"/register", RegisterHandler),
        (r"/login", LoginHandler),
        (r"/pharmacy", PharmacyHandler),
        (r"/pharmacy/([^/]+)", PharmacyHandler),
        (r"/category", CategoryHandler),
        (r"/category/([^/]+)", CategoryHandler),
        (r"/pharmacy/([^/]+)/category", PharmacyCategoryHandler),
        (r"/pharmacy/([^/]+)/category/([^/]+)", PharmacyCategoryHandler),
        (r"/medicine", MedicineHandler),
        (r"/medicine/([^/]+)", MedicineHandler),
        (r"/medicine/([^/]+)/sale", MedicineHandler),
        # (r"/medicine/category/([^/]+)", MedicineByCategoryHandler),
        (r"/sales", SalesHandler),
        (r"/sales/([^/]+)", SalesHandler),
         # New handler for downloading sales reports
        # (r"/sales/report/([^/]+)/([^/]+)", SalesReportHandler),
        (r"/sales/report/([^/]+)/([^/]+)", SalesHandler),
       
        #(r"/sales/report/([^/]+)", SalesReportHandler),  
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    print("Server started at http://localhost:8888")
    tornado.ioloop.IOLoop.current().start()
