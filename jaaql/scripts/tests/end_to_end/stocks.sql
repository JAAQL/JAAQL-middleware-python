create schema if not exists jaaql_test_schema;

create table if not exists jaaql_test_schema.exchange (
    name varchar(10) not null,
    country varchar(2) not null,
    incorporation_date date not null,
    PRIMARY KEY (name)
);

INSERT INTO jaaql_test_schema.exchange (name, country, incorporation_date) VALUES ('NASDAQ', 'US', '1971/02/08') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.exchange (name, country, incorporation_date) VALUES ('NYSE', 'US', '1792/05/17') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.exchange (name, country, incorporation_date) VALUES ('LON', 'GB', '1801/12/30') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.exchange (name, country, incorporation_date) VALUES ('AMS', 'NL', '1602/01/01') ON CONFLICT DO NOTHING;

create table if not exists jaaql_test_schema.ticker (
    exchange varchar(10) not null,
    symbol varchar(8) not null,
    started_trading date not null,
    PRIMARY KEY (exchange, symbol),
    FOREIGN KEY (exchange) REFERENCES jaaql_test_schema.exchange
);

INSERT INTO jaaql_test_schema.ticker (exchange, symbol, started_trading) VALUES ('NASDAQ', 'TSLA', '2010/06/01') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker (exchange, symbol, started_trading) VALUES ('NASDAQ', 'AMZN', '1997/05/15') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker (exchange, symbol, started_trading) VALUES ('NASDAQ', 'AAPL', '1981/04/03  ') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker (exchange, symbol, started_trading) VALUES ('NYSE', 'BRK.A', '1965/01/01') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker (exchange, symbol, started_trading) VALUES ('NYSE', 'JPM', '1981/04/03') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker (exchange, symbol, started_trading) VALUES ('LON', 'TSCO', '1995/01/06') ON CONFLICT DO NOTHING;

create table if not exists jaaql_test_schema.ticker_daily_aggregates (
    exchange varchar(10) not null,
    symbol varchar(8) not null,
    date date not null,
    volume double precision not null,
    PRIMARY KEY (exchange, symbol, date),
    FOREIGN KEY (exchange, symbol) REFERENCES jaaql_test_schema.ticker,
    FOREIGN KEY (exchange) REFERENCES jaaql_test_schema.exchange
);

INSERT INTO jaaql_test_schema.ticker_daily_aggregates (exchange, symbol, date, volume) VALUES ('NASDAQ', 'TSLA', '2020/03/01', 100) ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker_daily_aggregates (exchange, symbol, date, volume) VALUES ('NASDAQ', 'TSLA', '2020/03/02', 120) ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker_daily_aggregates (exchange, symbol, date, volume) VALUES ('NASDAQ', 'TSLA', '2020/03/03', 80) ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker_daily_aggregates (exchange, symbol, date, volume) VALUES ('NASDAQ', 'AMZN', '2020/03/02', 200) ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker_daily_aggregates (exchange, symbol, date, volume) VALUES ('NYSE', 'BRK.A', '2020/04/01', 500) ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker_daily_aggregates (exchange, symbol, date, volume) VALUES ('NYSE', 'BRK.A', '2020/04/02', 400) ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker_daily_aggregates (exchange, symbol, date, volume) VALUES ('LON', 'TSCO', '2020/03/01', 110) ON CONFLICT DO NOTHING;

create table if not exists jaaql_test_schema.alert (
    id int PRIMARY KEY NOT NULL,
    code varchar(10),
    description varchar(255)
);

INSERT INTO jaaql_test_schema.alert (id, code, description) VALUES (0, 'HALT', 'The trading has been halted') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.alert (id, code, description) VALUES (1, 'RESUME', 'The trading has been resumed') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.alert (id, code, description) VALUES (2, 'SPLIT', 'A stock split has occurred') ON CONFLICT DO NOTHING;

create table if not exists jaaql_test_schema.ticker_alert (
    alert int not null,
    exchange varchar(10) not null,
    symbol varchar(8) not null,
    occured timestamp not null,
    PRIMARY KEY (exchange, symbol, occured),
    FOREIGN KEY (alert) REFERENCES jaaql_test_schema.alert
);

CREATE INDEX IF NOT EXISTS ticker_alert_alert_index ON jaaql_test_schema.ticker_alert (alert);

INSERT INTO jaaql_test_schema.ticker_alert (alert, exchange, symbol, occured) VALUES (0, 'NASDAQ', 'TSLA', '2021-03-01 14:55:33.510000') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker_alert (alert, exchange, symbol, occured) VALUES (1, 'NASDAQ', 'TSLA', '2021-03-01 15:34:26.010000') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker_alert (alert, exchange, symbol, occured) VALUES (2, 'NASDAQ', 'TSLA', '2021-03-04 12:23:58.920000') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.ticker_alert (alert, exchange, symbol, occured) VALUES (2, 'NYSE', 'JPM', '2021-03-16 09:47:12.890000') ON CONFLICT DO NOTHING;

create table if not exists jaaql_test_schema.exchange_holiday (
    exchange varchar(10) not null,
    holiday_date date not null,
    description varchar(50),
    PRIMARY KEY (exchange, holiday_date),
    FOREIGN KEY (exchange) REFERENCES jaaql_test_schema.exchange
);

INSERT INTO jaaql_test_schema.exchange_holiday (exchange, holiday_date, description) VALUES ('NASDAQ', '2020-12-25', 'Christmas Day') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.exchange_holiday (exchange, holiday_date, description) VALUES ('NASDAQ', '2020-12-26', 'Boxing Day') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.exchange_holiday (exchange, holiday_date, description) VALUES ('LON', '2021-01-01', 'New Year''s Day') ON CONFLICT DO NOTHING;
INSERT INTO jaaql_test_schema.exchange_holiday (exchange, holiday_date, description) VALUES ('AMS', '2021-04-27', 'Koningsdag') ON CONFLICT DO NOTHING;
