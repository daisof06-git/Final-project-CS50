CREATE TABLE users(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username TEXT NOT NULL, 
    hash TEXT NOT NULL, 
    email TEXT UNIQUE NOT NULL);
CREATE UNIQUE INDEX username ON users (username);

CREATE TABLE jars(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    jar_name TEXT NOT NULL, 
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE UNIQUE INDEX jar_name ON jars (jar_name);

CREATE TABLE movements(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    amount NUMERIC NOT NULL,
    jar_id INTEGER,
    type TEXT NOT NULL CHECK((type = 'jar' AND jar_id IS NOT NULL) OR
    (type IN ('income','savings') AND jar_id IS NULL)), 
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    FOREIGN KEY(user_id) REFERENCES users(id), 
    FOREIGN KEY(jar_id) REFERENCES jars(id) 
    ON DELETE CASCADE
);

CREATE TABLE budget(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    amount NUMERIC,
    jar_id INTEGER,
    type TEXT NOT NULL CHECK((type = 'jar' AND jar_id IS NOT NULL) OR
    (type IN ('income','savings') AND jar_id IS NULL)), 
    FOREIGN KEY(user_id) REFERENCES users(id), 
    FOREIGN KEY(jar_id) REFERENCES jars(id)
    ON DELETE CASCADE,
    UNIQUE(user_id, jar_id, type)
);
