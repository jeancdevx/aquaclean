CREATE OR REPLACE FUNCTION app.check_embedding_dimension() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_dimension int;
BEGIN
  SELECT dimension INTO expected_dimension FROM app.collections WHERE id=NEW.collection_id;
  IF expected_dimension IS NULL OR vector_dims(NEW.embedding) <> expected_dimension THEN
    RAISE EXCEPTION 'Embedding dimension does not match collection';
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS check_embedding_dimension ON app.chunks;
CREATE TRIGGER check_embedding_dimension BEFORE INSERT OR UPDATE ON app.chunks FOR EACH ROW EXECUTE FUNCTION app.check_embedding_dimension();
CREATE OR REPLACE FUNCTION app.immutable_embedding_collection() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.model<>OLD.model OR NEW.dimension<>OLD.dimension THEN
    RAISE EXCEPTION 'Create a new collection when changing model or dimension';
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS immutable_embedding_collection ON app.collections;
CREATE TRIGGER immutable_embedding_collection BEFORE UPDATE ON app.collections FOR EACH ROW EXECUTE FUNCTION app.immutable_embedding_collection();
