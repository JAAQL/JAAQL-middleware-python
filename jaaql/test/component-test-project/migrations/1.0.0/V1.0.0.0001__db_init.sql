CREATE TABLE ctp_table (
    the_key integer PRIMARY KEY not null,
    the_data varchar(1)
);

INSERT INTO ctp_table (the_key, the_data) VALUES (1, 'a'), (2, 'c'), (3, 'b'), (5, 'd'), (4, 'e');