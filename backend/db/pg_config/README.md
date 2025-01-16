Things I changed within postgresql.conf
 - max connections is up to 105 (primarily for testing purposes)
 - Assuming that this database is running on Linux-like machines, the `dynamic_shared_memory_type` parameter is `posix`
 - locale settings are changes to `en_US.utf8`