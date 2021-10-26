# Examples

## Base Keywords
Base keywords are non SQL keywords. These are *parameters*, *echo* and *query* and *queries* currently. They are case sensitive unlike SQL keywords

## Query as string
No restrictions on query  
Returns result as dict
```sql
SELECT * FROM project_management.project
```

## Array of string queries as string
No restrictions on query  
Returns result as dict
```json
["SELECT * FROM project_management.project", "SELECT * FROM project_management.status"]
```

## Query as string defined within
No restrictions on query, parameters must a dictionary. Only base keywords allowed in base dictionary  
Returns result as dict
```json
{
    "parameters": {
        "status": "In Progress"
    },
    "query": "SELECT * FROM project_management.project p INNER JOIN project_management.status s ON s.id = p.status WHERE status = :status",
    "echo": true
}
```

## Multiple queries as string defined within
No restrictions on query, parameters must a list that matches length of queries list. Only base keywords (excluding *query*) allowed in base dictionary  
Returns result as dict
```json
{
    "parameters": [{
        "status": "In Progress"
    }],
    "queries": ["SELECT * FROM project_management.project p INNER JOIN project_management.status s ON s.id = p.status WHERE status = :status"],
    "echo": true
}
```

## Degenerate case
Restrictions placed on what is and isn't query. Only allowed: *select*, *from*, *join* (and all postgres joins), *where*, *group* (and variations such as *group by*), *having*, *order* (and variations such as *order by*). Also allowed base keywords (excluding *query* and *queries*). Any other keywords will cause error  
Returns result as dict
```json
{
    "parameters": {
        "status": "In Progress"
    },
    "select": {
        "Name": "p.name",
        "Creation Date": "p.created",
        "Project Description": "p.description",
        "Status": "s.status"
    },
    "from": "project_management.project p",
    "join": "project_management.status s ON s.id = p.status",
    "where": "s.status = :status",
    "order": "created asc",
    "echo": true
}
```

## Single query defined within, parameters in base
No restrictions on query, parameters must also be dictionary and not list. Only base keywords (excluding *queries*) allowed in base dictionary  
Returns result as dict
```json
{
    "parameters": {
        "status": "In Progress"
    },
    "query": {
        "select": {
            "Name": "p.name",
            "Creation Date": "p.created",
            "Project Description": "p.description",
            "Status": "s.status"
        },
        "from": "project_management.project p",
        "join": "project_management.status s ON s.id = p.status",
        "where": "s.status = :status",
        "order": "created asc"
    },
    "echo": true
}
```

## Single query defined within, parameters in query
No restrictions on query, parameters must also be dictionary and not list. Only base keywords (minus *parameters* and *queries*) allowed in base dictionary. Placing *parameters* in base will cause error  
Returns result as dict
```json
{
    "query": {
        "parameters": {
            "status": "In Progress"
        },
        "select": {
            "Name": "p.name",
            "Creation Date": "p.created",
            "Project Description": "p.description",
            "Status": "s.status"
        },
        "from": "project_management.project p",
        "join": "project_management.status s ON s.id = p.status",
        "where": "s.status = :status",
        "order": "created asc"
    },
    "echo": true
}
```

## Multiple query defined within, parameters in base
No restrictions on query, parameters must also be list and not dictionary and match length of query. Only base keywords (excluding *query*) allowed in base dictionary  
Returns result as list of dicts
```json
{
    "parameters": [{
        "status": "In Progress"
    }],
    "queries": [{
        "select": {
            "Name": "p.name",
            "Creation Date": "p.created",
            "Project Description": "p.description",
            "Status": "s.status"
        },
        "from": "project_management.project p",
        "join": "project_management.status s ON s.id = p.status",
        "where": "s.status = :status",
        "order": "created asc"
    }],
    "echo": true
}
```

## Multiple query defined within, parameters in query
No restrictions on query. Only base keywords (minus *parameters* and *queries*) allowed in base dictionary. Placing *parameters* in base will cause error  
Returns result as list of dicts
```json
{
    "queries": [{
        "parameters": {
            "status": "In Progress"
        },
        "select": {
            "Name": "p.name",
            "Creation Date": "p.created",
            "Project Description": "p.description",
            "Status": "s.status"
        },
        "from": "project_management.project p",
        "join": "project_management.status s ON s.id = p.status",
        "where": "s.status = :status",
        "order": "created asc"
    }],
    "echo": true
}
```
