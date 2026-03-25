
CREATE TABLE cosmic_country_shows_raw (
    id SERIAL PRIMARY KEY,
    show_id VARCHAR(50) UNIQUE NOT NULL,
    show_date DATE NOT NULL,
    venue_name VARCHAR(255),
    venue_city VARCHAR(100),
    venue_state VARCHAR(50),
    venue_country VARCHAR(50),
    tour_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cosmic_country_setlists_raw (
    id SERIAL PRIMARY KEY,
    show_id VARCHAR(50) NOT NULL,
    set_number INTEGER NOT NULL,
    song_position INTEGER NOT NULL,
    song_name VARCHAR(255) NOT NULL,
    song_length INTEGER, -- seconds
    encore BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (show_id) REFERENCES cosmic_country_shows_raw(show_id)
);

CREATE TABLE cosmic_country_songs_raw (
    id SERIAL PRIMARY KEY,
    song_name VARCHAR(255) UNIQUE NOT NULL,
    first_played DATE,
    last_played DATE,
    times_played INTEGER DEFAULT 0,
    average_length INTEGER, -- seconds
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
;
