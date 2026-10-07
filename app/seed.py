from app.models import SessionLocal, User, Movie, Snack

MOVIES = [
    ("Blood Feast II", "Horror", 1986), ("Cyber Ninja", "Action", 1988),
    ("Starlite Zone", "SciFi", 1985), ("Love on Aisle 9", "Romance", 1987),
    ("Night of the Rewind", "Horror", 1989), ("Turbo Cop", "Action", 1990),
    ("Galaxy Rental", "SciFi", 1984), ("The Last Betamax", "Drama", 1991),
    ("Neon Drifter", "Action", 1986), ("VHS Vendetta", "Thriller", 1988),
    ("Arcade Avengers", "SciFi", 1989), ("Midnight Modem", "Thriller", 1992),
    ("Disco Werewolf", "Horror", 1983), ("Satellite Hearts", "Romance", 1990),
    ("Rewind or Die", "Action", 1993),
]

SNACKS = [("Popcorn", 2.50), ("Soda", 1.00), ("Blank VHS", 5.00)]


def seed():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(User(username="guest", password="guest", balance=5.0, is_admin=False, email="guest@starlite.bbs"))
            db.add(User(username="admin", password="admin123", balance=999.0, is_admin=True, email="sysop@starlite.bbs"))
        if db.query(Movie).count() == 0:
            for title, genre, year in MOVIES:
                db.add(Movie(title=title, genre=genre, year=year, rental_price=2.0, stock=3))
        if db.query(Snack).count() == 0:
            for name, price in SNACKS:
                db.add(Snack(name=name, price=price, stock=100))
        db.commit()
    finally:
        db.close()
