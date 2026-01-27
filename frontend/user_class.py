from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, first_name, last_name, username, email):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.email = email