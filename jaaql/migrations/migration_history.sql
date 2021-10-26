create table migration_history
(
    project_name   varchar(100)            not null,
    installed_rank integer                 not null,
    version        varchar(50),
    description    varchar(200)            not null,
    type           varchar(20)             default 'SQL' not null,
    script         varchar(1000)           not null,
    checksum       integer,
    installed_by   varchar(100)            default current_user not null,
    installed_on   timestamp default now() not null,
    execution_time integer                 not null,
    success        boolean                 default true not null,
    PRIMARY KEY (project_name, installed_rank)
);
