from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, first_name, last_name, username, email):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.email = email

    @classmethod
    def from_db_row(cls, row):
        return cls(id=row['id'], first_name=row['first_name'], last_name=row['last_name'],
                   username=row['username'], email=row['email'])
