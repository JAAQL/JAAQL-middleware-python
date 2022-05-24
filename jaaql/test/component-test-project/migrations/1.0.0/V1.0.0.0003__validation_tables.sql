create table ctp_data_signup_table (
    id uuid not null default gen_random_uuid(),
    name varchar(10),
    city varchar(50),
    check (city in ('Helena', 'Bozeman', 'Billings'))
);

create table ctp_data_validation_table (
    id uuid not null default gen_random_uuid(),
    ctp_replace varchar(10),
    check (ctp_replace in ('apple', 'banana', 'pear'))
);

create view ctp_data_validation_view as (
    SELECT
        id,
        ctp_replace,
        'replacement_value' as replacement_value
    FROM
        ctp_data_validation_table
);

create table ctp_recipient_validation_view as (
    SELECT current_user
);