CREATE TABLE users(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username TEXT NOT NULL, 
    hash TEXT NOT NULL, 
    balance NUMERIC,
    email TEXT UNIQUE NOT NULL);
CREATE UNIQUE INDEX username ON users (username);

CREATE TABLE jars(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    jar_name TEXT NOT NULL, 
    amount NUMERIC, 
    FOREIGN KEY(user_id) REFERENCES users(id));

CREATE TABLE movements(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    amount NUMERIC NOT NULL,
    new_jar_id INTEGER NOT NULL, 
    last_jar_id INTEGER NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    FOREIGN KEY(user_id) REFERENCES users(id), 
    FOREIGN KEY(new_jar_id) REFERENCES jars(id), 
    FOREIGN KEY(last_jar_id) REFERENCES jars(id)); 
