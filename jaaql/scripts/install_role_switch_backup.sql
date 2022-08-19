create table jaaql__function
(
    name postgres_addressable_name
);
INSERT INTO jaaql__function (name) VALUES
                                          (''), (''), (''),
                                          (''), (''), (''),
                                          (''), (''), ('');

create or replace function __jaaql_function_wrapper(func_name postgres_addressable_name, parameters text[]) returns void as
$$
DECLARE
    the_user jaaql_account_id;
    exec_func postgres_addressable_name;
    user_vals text;
    func_oid oid;
BEGIN
    SELECT '__' || name, current_user INTO exec_func, the_user FROM jaaql__function WHERE name = func_name AND has_function_privilege(name, 'EXECUTE');
    if the_user is not null and exec_func is not null then
        parameters = ARRAY[the_user::text] || parameters;
        RESET ROLE;
    else
        exec_func = func_name;  -- Will provide the correct error such as lacks access or function does not exist
    end if;

    select oid into func_oid from pg_proc where proname = exec_func;

    SELECT string_agg(res, ', ') into user_vals
    FROM
        (SELECT quote_literal(val) || '::' || split_part(TYPE, ' ', 2) AS res
        FROM unnest(string_to_array(pg_get_function_identity_arguments(func_oid), ', '), parameters) AS u(TYPE, val)) res;

    EXECUTE 'SELECT ' || quote_ident(func_name) || '($1)' USING the_user;

    -- TODO incorrect number of arguments error handling etc.

    if the_user is not null and exec_func is not null then
        SET ROLE the_user;
    end if;
END
$$ language plpgsql;
GRANT execute on function __jaaql_function_wrapper() TO public;