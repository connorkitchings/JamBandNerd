# AllThingsUM Data Schema

## setlistdata.csv
| Column        | Type    | Description                                        |
|---------------|---------|----------------------------------------------------|
| song          | string  | Song name                                          |
| set           | int     | Set number                                         |
| in_set_index  | float   | Position in set                                    |
| in_show_index | float   | Position in show                                   |
| footnotes     | string  | Notes or footnotes                                 |
| date          | date    | Date of show (MM/DD/YYYY)                          |
| venue         | string  | Venue name                                         |
| city          | string  | City                                               |
| state         | string  | State                                              |
| country       | string  | Country                                            |
| link          | string  | URL to show                                        |
| set_index     | float   | Set index (may be empty)                           |
| show_index    | float   | Show index (may be empty)                          |

## showdata.csv
| Column      | Type    | Description                                        |
|-------------|---------|----------------------------------------------------|
| link        | string  | URL to show                                        |
| date        | date    | Date of show (MM/DD/YYYY)                          |
| venue       | string  | Venue name                                         |
| city        | string  | City                                               |
| state       | string  | State                                              |
| country     | string  | Country                                            |
| show_number | int     | Sequential show number                             |

## songdata.csv
| Column            | Type    | Description                                    |
|-------------------|---------|------------------------------------------------|
| Song Name         | string  | Song name                                      |
| Original Artist   | string  | Original artist                                |
| Debut Date        | date    | Debut date (YYYY-MM-DD)                        |
| Last Played       | date    | Last played date (YYYY-MM-DD)                  |
| Times Played Live | int     | Number of times played live                    |
| Avg Show Gap      | float   | Average number of shows between plays          |

## venuedata.csv
| Column        | Type    | Description                                     |
|---------------|---------|-------------------------------------------------|
| id            | int     | Venue identifier                                |
| Venue Name    | string  | Venue name                                      |
| City          | string  | City                                            |
| State         | string  | State                                           |
| Country       | string  | Country                                         |
| Times Played  | int     | Number of times played at this venue            |
| Last Played   | date    | Last played date (YYYY-MM-DD)                   |
