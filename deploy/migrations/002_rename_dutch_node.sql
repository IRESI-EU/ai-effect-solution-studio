BEGIN;

ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_node;

UPDATE users
SET node = 'dutch'
WHERE node = 'netherlands';

UPDATE services
SET owner_node = 'dutch'
WHERE owner_node = 'netherlands';

ALTER TABLE users
    ADD CONSTRAINT ck_users_node
    CHECK (node IS NULL OR node IN ('germany', 'portugal', 'denmark', 'dutch'));

COMMIT;
