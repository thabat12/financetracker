PREPARE account_update_test AS
    INSERT INTO account (account_id, balance_available, balance_current, iso_currency_code, account_name, account_type, update_status, update_status_date, user_id, institution_id)
            VALUES ('ZlnQE7gPVmhBblw68jr7uaa14eZ7MAseaGbXm', $1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (account_id)
            DO UPDATE SET
                balance_available=EXCLUDED.balance_available,
                balance_current = EXCLUDED.balance_current,
                update_status = EXCLUDED.update_status,
                update_status_date = EXCLUDED.update_status_date;

EXECUTE account_update_test(
    b'F\xa8>!\xa3\xd8\x95&\x01\xc0\x02\xf6;.$\xeeBNv[\xf7&B\x01\xfe3\x95hHW=\x93',
    b'{o\x80\x1f\xe0k\x07\xa8\xf3U\xbb\xfa\x16c\xe4\xe4\xfbgZ\xee_\x82\\"L\x83\xd7\x88K\xd9v\xb5',
    'USD',
    b'\x18?+\n\t\x96\xdf\xf6\x96\x96\xd3*\x08f\xe2\xb6Y\x80ay\xa4\x1f\x88\x88\xe9\x99\xc8\x83+\x9aC?',
    b"\xf4\xda\x91Y\x9e\x11~}'O\xc4\xf6\x0e\xc4\x06\xd3\xcf\xcd\xc4\n\x1c\xd7h\x96g\xe1\xe1%\x88A\x94\xdb",
    'added',
    '2024-10-23 20:29:01.177532'
);

DEALLOCATE account_update_test;