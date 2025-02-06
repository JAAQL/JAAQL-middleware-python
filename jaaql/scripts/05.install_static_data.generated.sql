

-- (3) Populate tables

-- jaaql...
insert into jaaql (security_event_attempt_limit, migration_version, last_successful_build_time)
values (3, '1.0.2', 0);

;
-- pg_base_exception...
insert into pg_base_exception (name)
values ('DatabaseError'),
		('OperationalError'),
		('NotSupportedError'),
		('ProgrammingError'),
		('DataError'),
		('IntegrityError'),
		('InternalError');

;
-- pg_error_class...
insert into pg_error_class (code, name, description)
values ('02', 'NO_DATA', 'this is also a warning class per the SQL standard'),
		('03', 'SQL_STATEMENT_NOT_YET_COMPLETE', NULL),
		('08', 'CONNECTION_EXCEPTION', NULL),
		('09', 'TRIGGERED_ACTION_EXCEPTION', NULL),
		('0A', 'FEATURE_NOT_SUPPORTED', NULL),
		('0B', 'INVALID_TRANSACTION_INITIATION', NULL),
		('0F', 'LOCATOR_EXCEPTION', NULL),
		('0L', 'INVALID_GRANTOR', NULL),
		('0P', 'INVALID_ROLE_SPECIFICATION', NULL),
		('0Z', 'DIAGNOSTICS_EXCEPTION', NULL),
		('20', 'CASE_NOT_FOUND', NULL),
		('21', 'CARDINALITY_VIOLATION', NULL),
		('22', 'DATA_EXCEPTION', NULL),
		('23', 'INTEGRITY_CONSTRAINT_VIOLATION', NULL),
		('24', 'INVALID_CURSOR_STATE', NULL),
		('25', 'INVALID_TRANSACTION_STATE', NULL),
		('26', 'INVALID_SQL_STATEMENT_NAME', NULL),
		('27', 'TRIGGERED_DATA_CHANGE_VIOLATION', NULL),
		('28', 'INVALID_AUTHORIZATION_SPECIFICATION', NULL),
		('2B', 'DEPENDENT_PRIVILEGE_DESCRIPTORS_STILL_EXIST', NULL);
insert into pg_error_class (code, name, description)
values ('2D', 'INVALID_TRANSACTION_TERMINATION', NULL),
		('2F', 'SQL_ROUTINE_EXCEPTION', NULL),
		('34', 'INVALID_CURSOR_NAME', NULL),
		('38', 'EXTERNAL_ROUTINE_EXCEPTION', NULL),
		('39', 'EXTERNAL_ROUTINE_INVOCATION_EXCEPTION', NULL),
		('3B', 'SAVEPOINT_EXCEPTION', NULL),
		('3D', 'INVALID_CATALOG_NAME', NULL),
		('3F', 'INVALID_SCHEMA_NAME', NULL),
		('40', 'TRANSACTION_ROLLBACK', NULL),
		('42', 'SYNTAX_ERROR_OR_ACCESS_RULE_VIOLATION', NULL),
		('44', 'WITH_CHECK_OPTION_VIOLATION', NULL),
		('53', 'INSUFFICIENT_RESOURCES', NULL),
		('54', 'PROGRAM_LIMIT_EXCEEDED', NULL),
		('55', 'OBJECT_NOT_IN_PREREQUISITE_STATE', NULL),
		('57', 'OPERATOR_INTERVENTION', NULL),
		('58', 'SYSTEM_ERROR', 'errors external to PostgreSQL itself'),
		('72', 'SNAPSHOT_FAILURE', NULL),
		('F0', 'CONFIGURATION_FILE_ERROR', NULL),
		('HV', 'FOREIGN_DATA_WRAPPER_ERROR', 'SQL/MED'),
		('P0', 'PL/PGSQL_ERROR', NULL);
insert into pg_error_class (code, name, description)
values ('XX', 'INTERNAL_ERROR', NULL);

;
-- pg_exception...
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('02', '02000', 'NoData', 'DatabaseError'),
		('02', '02001', 'NoAdditionalDynamicResultSetsReturned', 'DatabaseError'),
		('03', '03000', 'SqlStatementNotYetComplete', 'DatabaseError'),
		('08', '08000', 'ConnectionException', 'OperationalError'),
		('08', '08001', 'SqlclientUnableToEstablishSqlconnection', 'OperationalError'),
		('08', '08003', 'ConnectionDoesNotExist', 'OperationalError'),
		('08', '08004', 'SqlserverRejectedEstablishmentOfSqlconnection', 'OperationalError'),
		('08', '08006', 'ConnectionFailure', 'OperationalError'),
		('08', '08007', 'TransactionResolutionUnknown', 'OperationalError'),
		('08', '08P01', 'ProtocolViolation', 'OperationalError'),
		('09', '09000', 'TriggeredActionException', 'DatabaseError'),
		('0A', '0A000', 'FeatureNotSupported', 'NotSupportedError'),
		('0B', '0B000', 'InvalidTransactionInitiation', 'DatabaseError'),
		('0F', '0F000', 'LocatorException', 'DatabaseError'),
		('0F', '0F001', 'InvalidLocatorSpecification', 'DatabaseError'),
		('0L', '0L000', 'InvalidGrantor', 'DatabaseError'),
		('0L', '0LP01', 'InvalidGrantOperation', 'DatabaseError'),
		('0P', '0P000', 'InvalidRoleSpecification', 'DatabaseError'),
		('0Z', '0Z000', 'DiagnosticsException', 'DatabaseError'),
		('0Z', '0Z002', 'StackedDiagnosticsAccessedWithoutActiveHandler', 'DatabaseError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('20', '20000', 'CaseNotFound', 'ProgrammingError'),
		('21', '21000', 'CardinalityViolation', 'ProgrammingError'),
		('22', '22000', 'DataException', 'DataError'),
		('22', '22001', 'StringDataRightTruncation', 'DataError'),
		('22', '22002', 'NullValueNoIndicatorParameter', 'DataError'),
		('22', '22003', 'NumericValueOutOfRange', 'DataError'),
		('22', '22004', 'NullValueNotAllowed', 'DataError'),
		('22', '22005', 'ErrorInAssignment', 'DataError'),
		('22', '22007', 'InvalidDatetimeFormat', 'DataError'),
		('22', '22008', 'DatetimeFieldOverflow', 'DataError'),
		('22', '22009', 'InvalidTimeZoneDisplacementValue', 'DataError'),
		('22', '2200B', 'EscapeCharacterConflict', 'DataError'),
		('22', '2200C', 'InvalidUseOfEscapeCharacter', 'DataError'),
		('22', '2200D', 'InvalidEscapeOctet', 'DataError'),
		('22', '2200F', 'ZeroLengthCharacterString', 'DataError'),
		('22', '2200G', 'MostSpecificTypeMismatch', 'DataError'),
		('22', '2200H', 'SequenceGeneratorLimitExceeded', 'DataError'),
		('22', '2200L', 'NotAnXmlDocument', 'DataError'),
		('22', '2200M', 'InvalidXmlDocument', 'DataError'),
		('22', '2200N', 'InvalidXmlContent', 'DataError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('22', '2200S', 'InvalidXmlComment', 'DataError'),
		('22', '2200T', 'InvalidXmlProcessingInstruction', 'DataError'),
		('22', '22010', 'InvalidIndicatorParameterValue', 'DataError'),
		('22', '22011', 'SubstringError', 'DataError'),
		('22', '22012', 'DivisionByZero', 'DataError'),
		('22', '22013', 'InvalidPrecedingOrFollowingSize', 'DataError'),
		('22', '22014', 'InvalidArgumentForNtileFunction', 'DataError'),
		('22', '22015', 'IntervalFieldOverflow', 'DataError'),
		('22', '22016', 'InvalidArgumentForNthValueFunction', 'DataError'),
		('22', '22018', 'InvalidCharacterValueForCast', 'DataError'),
		('22', '22019', 'InvalidEscapeCharacter', 'DataError'),
		('22', '2201B', 'InvalidRegularExpression', 'DataError'),
		('22', '2201E', 'InvalidArgumentForLogarithm', 'DataError'),
		('22', '2201F', 'InvalidArgumentForPowerFunction', 'DataError'),
		('22', '2201G', 'InvalidArgumentForWidthBucketFunction', 'DataError'),
		('22', '2201W', 'InvalidRowCountInLimitClause', 'DataError'),
		('22', '2201X', 'InvalidRowCountInResultOffsetClause', 'DataError'),
		('22', '22021', 'CharacterNotInRepertoire', 'DataError'),
		('22', '22022', 'IndicatorOverflow', 'DataError'),
		('22', '22023', 'InvalidParameterValue', 'DataError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('22', '22024', 'UnterminatedCString', 'DataError'),
		('22', '22025', 'InvalidEscapeSequence', 'DataError'),
		('22', '22026', 'StringDataLengthMismatch', 'DataError'),
		('22', '22027', 'TrimError', 'DataError'),
		('22', '2202E', 'ArraySubscriptError', 'DataError'),
		('22', '2202G', 'InvalidTablesampleRepeat', 'DataError'),
		('22', '2202H', 'InvalidTablesampleArgument', 'DataError'),
		('22', '22030', 'DuplicateJsonObjectKeyValue', 'DataError'),
		('22', '22031', 'InvalidArgumentForSqlJsonDatetimeFunction', 'DataError'),
		('22', '22032', 'InvalidJsonText', 'DataError'),
		('22', '22033', 'InvalidSqlJsonSubscript', 'DataError'),
		('22', '22034', 'MoreThanOneSqlJsonItem', 'DataError'),
		('22', '22035', 'NoSqlJsonItem', 'DataError'),
		('22', '22036', 'NonNumericSqlJsonItem', 'DataError'),
		('22', '22037', 'NonUniqueKeysInAJsonObject', 'DataError'),
		('22', '22038', 'SingletonSqlJsonItemRequired', 'DataError'),
		('22', '22039', 'SqlJsonArrayNotFound', 'DataError'),
		('22', '2203A', 'SqlJsonMemberNotFound', 'DataError'),
		('22', '2203B', 'SqlJsonNumberNotFound', 'DataError'),
		('22', '2203C', 'SqlJsonObjectNotFound', 'DataError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('22', '2203D', 'TooManyJsonArrayElements', 'DataError'),
		('22', '2203E', 'TooManyJsonObjectMembers', 'DataError'),
		('22', '2203F', 'SqlJsonScalarRequired', 'DataError'),
		('22', '2203G', 'SqlJsonItemCannotBeCastToTargetType', 'DataError'),
		('22', '22P01', 'FloatingPointException', 'DataError'),
		('22', '22P02', 'InvalidTextRepresentation', 'DataError'),
		('22', '22P03', 'InvalidBinaryRepresentation', 'DataError'),
		('22', '22P04', 'BadCopyFileFormat', 'DataError'),
		('22', '22P05', 'UntranslatableCharacter', 'DataError'),
		('22', '22P06', 'NonstandardUseOfEscapeCharacter', 'DataError'),
		('23', '23000', 'IntegrityConstraintViolation', 'IntegrityError'),
		('23', '23001', 'RestrictViolation', 'IntegrityError'),
		('23', '23502', 'NotNullViolation', 'IntegrityError'),
		('23', '23503', 'ForeignKeyViolation', 'IntegrityError'),
		('23', '23505', 'UniqueViolation', 'IntegrityError'),
		('23', '23514', 'CheckViolation', 'IntegrityError'),
		('23', '23P01', 'ExclusionViolation', 'IntegrityError'),
		('24', '24000', 'InvalidCursorState', 'InternalError'),
		('25', '25000', 'InvalidTransactionState', 'InternalError'),
		('25', '25001', 'ActiveSqlTransaction', 'InternalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('25', '25002', 'BranchTransactionAlreadyActive', 'InternalError'),
		('25', '25003', 'InappropriateAccessModeForBranchTransaction', 'InternalError'),
		('25', '25004', 'InappropriateIsolationLevelForBranchTransaction', 'InternalError'),
		('25', '25005', 'NoActiveSqlTransactionForBranchTransaction', 'InternalError'),
		('25', '25006', 'ReadOnlySqlTransaction', 'InternalError'),
		('25', '25007', 'SchemaAndDataStatementMixingNotSupported', 'InternalError'),
		('25', '25008', 'HeldCursorRequiresSameIsolationLevel', 'InternalError'),
		('25', '25P01', 'NoActiveSqlTransaction', 'InternalError'),
		('25', '25P02', 'InFailedSqlTransaction', 'InternalError'),
		('25', '25P03', 'IdleInTransactionSessionTimeout', 'InternalError'),
		('26', '26000', 'InvalidSqlStatementName', 'ProgrammingError'),
		('27', '27000', 'TriggeredDataChangeViolation', 'OperationalError'),
		('28', '28000', 'InvalidAuthorizationSpecification', 'OperationalError'),
		('28', '28P01', 'InvalidPassword', 'OperationalError'),
		('2B', '2B000', 'DependentPrivilegeDescriptorsStillExist', 'InternalError'),
		('2B', '2BP01', 'DependentObjectsStillExist', 'InternalError'),
		('2D', '2D000', 'InvalidTransactionTermination', 'InternalError'),
		('2F', '2F000', 'SqlRoutineException', 'OperationalError'),
		('2F', '2F002', 'ModifyingSqlDataNotPermitted', 'OperationalError'),
		('2F', '2F003', 'ProhibitedSqlStatementAttempted', 'OperationalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('2F', '2F004', 'ReadingSqlDataNotPermitted', 'OperationalError'),
		('2F', '2F005', 'FunctionExecutedNoReturnStatement', 'OperationalError'),
		('34', '34000', 'InvalidCursorName', 'ProgrammingError'),
		('38', '38000', 'ExternalRoutineException', 'OperationalError'),
		('38', '38001', 'ContainingSqlNotPermitted', 'OperationalError'),
		('38', '38002', 'ModifyingSqlDataNotPermittedExt', 'OperationalError'),
		('38', '38003', 'ProhibitedSqlStatementAttemptedExt', 'OperationalError'),
		('38', '38004', 'ReadingSqlDataNotPermittedExt', 'OperationalError'),
		('39', '39000', 'ExternalRoutineInvocationException', 'OperationalError'),
		('39', '39001', 'InvalidSqlstateReturned', 'OperationalError'),
		('39', '39004', 'NullValueNotAllowedExt', 'OperationalError'),
		('39', '39P01', 'TriggerProtocolViolated', 'OperationalError'),
		('39', '39P02', 'SrfProtocolViolated', 'OperationalError'),
		('39', '39P03', 'EventTriggerProtocolViolated', 'OperationalError'),
		('3B', '3B000', 'SavepointException', 'OperationalError'),
		('3B', '3B001', 'InvalidSavepointSpecification', 'OperationalError'),
		('3D', '3D000', 'InvalidCatalogName', 'ProgrammingError'),
		('3F', '3F000', 'InvalidSchemaName', 'ProgrammingError'),
		('40', '40000', 'TransactionRollback', 'OperationalError'),
		('40', '40001', 'SerializationFailure', 'OperationalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('40', '40002', 'TransactionIntegrityConstraintViolation', 'OperationalError'),
		('40', '40003', 'StatementCompletionUnknown', 'OperationalError'),
		('40', '40P01', 'DeadlockDetected', 'OperationalError'),
		('42', '42000', 'SyntaxErrorOrAccessRuleViolation', 'ProgrammingError'),
		('42', '42501', 'InsufficientPrivilege', 'ProgrammingError'),
		('42', '42601', 'SyntaxError', 'ProgrammingError'),
		('42', '42602', 'InvalidName', 'ProgrammingError'),
		('42', '42611', 'InvalidColumnDefinition', 'ProgrammingError'),
		('42', '42622', 'NameTooLong', 'ProgrammingError'),
		('42', '42701', 'DuplicateColumn', 'ProgrammingError'),
		('42', '42702', 'AmbiguousColumn', 'ProgrammingError'),
		('42', '42703', 'UndefinedColumn', 'ProgrammingError'),
		('42', '42704', 'UndefinedObject', 'ProgrammingError'),
		('42', '42710', 'DuplicateObject', 'ProgrammingError'),
		('42', '42712', 'DuplicateAlias', 'ProgrammingError'),
		('42', '42723', 'DuplicateFunction', 'ProgrammingError'),
		('42', '42725', 'AmbiguousFunction', 'ProgrammingError'),
		('42', '42803', 'GroupingError', 'ProgrammingError'),
		('42', '42804', 'DatatypeMismatch', 'ProgrammingError'),
		('42', '42809', 'WrongObjectType', 'ProgrammingError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('42', '42830', 'InvalidForeignKey', 'ProgrammingError'),
		('42', '42846', 'CannotCoerce', 'ProgrammingError'),
		('42', '42883', 'UndefinedFunction', 'ProgrammingError'),
		('42', '428C9', 'GeneratedAlways', 'ProgrammingError'),
		('42', '42939', 'ReservedName', 'ProgrammingError'),
		('42', '42P01', 'UndefinedTable', 'ProgrammingError'),
		('42', '42P02', 'UndefinedParameter', 'ProgrammingError'),
		('42', '42P03', 'DuplicateCursor', 'ProgrammingError'),
		('42', '42P04', 'DuplicateDatabase', 'ProgrammingError'),
		('42', '42P05', 'DuplicatePreparedStatement', 'ProgrammingError'),
		('42', '42P06', 'DuplicateSchema', 'ProgrammingError'),
		('42', '42P07', 'DuplicateTable', 'ProgrammingError'),
		('42', '42P08', 'AmbiguousParameter', 'ProgrammingError'),
		('42', '42P09', 'AmbiguousAlias', 'ProgrammingError'),
		('42', '42P10', 'InvalidColumnReference', 'ProgrammingError'),
		('42', '42P11', 'InvalidCursorDefinition', 'ProgrammingError'),
		('42', '42P12', 'InvalidDatabaseDefinition', 'ProgrammingError'),
		('42', '42P13', 'InvalidFunctionDefinition', 'ProgrammingError'),
		('42', '42P14', 'InvalidPreparedStatementDefinition', 'ProgrammingError'),
		('42', '42P15', 'InvalidSchemaDefinition', 'ProgrammingError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('42', '42P16', 'InvalidTableDefinition', 'ProgrammingError'),
		('42', '42P17', 'InvalidObjectDefinition', 'ProgrammingError'),
		('42', '42P18', 'IndeterminateDatatype', 'ProgrammingError'),
		('42', '42P19', 'InvalidRecursion', 'ProgrammingError'),
		('42', '42P20', 'WindowingError', 'ProgrammingError'),
		('42', '42P21', 'CollationMismatch', 'ProgrammingError'),
		('42', '42P22', 'IndeterminateCollation', 'ProgrammingError'),
		('44', '44000', 'WithCheckOptionViolation', 'ProgrammingError'),
		('53', '53000', 'InsufficientResources', 'OperationalError'),
		('53', '53100', 'DiskFull', 'OperationalError'),
		('53', '53200', 'OutOfMemory', 'OperationalError'),
		('53', '53300', 'TooManyConnections', 'OperationalError'),
		('53', '53400', 'ConfigurationLimitExceeded', 'OperationalError'),
		('54', '54000', 'ProgramLimitExceeded', 'OperationalError'),
		('54', '54001', 'StatementTooComplex', 'OperationalError'),
		('54', '54011', 'TooManyColumns', 'OperationalError'),
		('54', '54023', 'TooManyArguments', 'OperationalError'),
		('55', '55000', 'ObjectNotInPrerequisiteState', 'OperationalError'),
		('55', '55006', 'ObjectInUse', 'OperationalError'),
		('55', '55P02', 'CantChangeRuntimeParam', 'OperationalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('55', '55P03', 'LockNotAvailable', 'OperationalError'),
		('55', '55P04', 'UnsafeNewEnumValueUsage', 'OperationalError'),
		('57', '57000', 'OperatorIntervention', 'OperationalError'),
		('57', '57014', 'QueryCanceled', 'OperationalError'),
		('57', '57P01', 'AdminShutdown', 'OperationalError'),
		('57', '57P02', 'CrashShutdown', 'OperationalError'),
		('57', '57P03', 'CannotConnectNow', 'OperationalError'),
		('57', '57P04', 'DatabaseDropped', 'OperationalError'),
		('57', '57P05', 'IdleSessionTimeout', 'OperationalError'),
		('58', '58000', 'SystemError', 'OperationalError'),
		('58', '58030', 'IoError', 'OperationalError'),
		('58', '58P01', 'UndefinedFile', 'OperationalError'),
		('58', '58P02', 'DuplicateFile', 'OperationalError'),
		('72', '72000', 'SnapshotTooOld', 'DatabaseError'),
		('F0', 'F0000', 'ConfigFileError', 'OperationalError'),
		('F0', 'F0001', 'LockFileExists', 'OperationalError'),
		('HV', 'HV000', 'FdwError', 'OperationalError'),
		('HV', 'HV001', 'FdwOutOfMemory', 'OperationalError'),
		('HV', 'HV002', 'FdwDynamicParameterValueNeeded', 'OperationalError'),
		('HV', 'HV004', 'FdwInvalidDataType', 'OperationalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('HV', 'HV005', 'FdwColumnNameNotFound', 'OperationalError'),
		('HV', 'HV006', 'FdwInvalidDataTypeDescriptors', 'OperationalError'),
		('HV', 'HV007', 'FdwInvalidColumnName', 'OperationalError'),
		('HV', 'HV008', 'FdwInvalidColumnNumber', 'OperationalError'),
		('HV', 'HV009', 'FdwInvalidUseOfNullPointer', 'OperationalError'),
		('HV', 'HV00A', 'FdwInvalidStringFormat', 'OperationalError'),
		('HV', 'HV00B', 'FdwInvalidHandle', 'OperationalError'),
		('HV', 'HV00C', 'FdwInvalidOptionIndex', 'OperationalError'),
		('HV', 'HV00D', 'FdwInvalidOptionName', 'OperationalError'),
		('HV', 'HV00J', 'FdwOptionNameNotFound', 'OperationalError'),
		('HV', 'HV00K', 'FdwReplyHandle', 'OperationalError'),
		('HV', 'HV00L', 'FdwUnableToCreateExecution', 'OperationalError'),
		('HV', 'HV00M', 'FdwUnableToCreateReply', 'OperationalError'),
		('HV', 'HV00N', 'FdwUnableToEstablishConnection', 'OperationalError'),
		('HV', 'HV00P', 'FdwNoSchemas', 'OperationalError'),
		('HV', 'HV00Q', 'FdwSchemaNotFound', 'OperationalError'),
		('HV', 'HV00R', 'FdwTableNotFound', 'OperationalError'),
		('HV', 'HV010', 'FdwFunctionSequenceError', 'OperationalError'),
		('HV', 'HV014', 'FdwTooManyHandles', 'OperationalError'),
		('HV', 'HV021', 'FdwInconsistentDescriptorInformation', 'OperationalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('HV', 'HV024', 'FdwInvalidAttributeValue', 'OperationalError'),
		('HV', 'HV090', 'FdwInvalidStringLengthOrBufferLength', 'OperationalError'),
		('HV', 'HV091', 'FdwInvalidDescriptorFieldIdentifier', 'OperationalError'),
		('P0', 'P0000', 'PlpgsqlError', 'ProgrammingError'),
		('P0', 'P0001', 'RaiseException', 'ProgrammingError'),
		('P0', 'P0002', 'NoDataFound', 'ProgrammingError'),
		('P0', 'P0003', 'TooManyRows', 'ProgrammingError'),
		('P0', 'P0004', 'AssertFailure', 'ProgrammingError'),
		('XX', 'XX000', 'InternalError_', 'InternalError'),
		('XX', 'XX001', 'DataCorrupted', 'InternalError');

;