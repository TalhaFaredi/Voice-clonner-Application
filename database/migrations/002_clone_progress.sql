ALTER TABLE voices ADD COLUMN reference_duration REAL;
ALTER TABLE voices ADD COLUMN clone_mode TEXT NOT NULL DEFAULT 'speaker_embedding';
ALTER TABLE voices ADD COLUMN preview_text TEXT NOT NULL DEFAULT '';
ALTER TABLE voices ADD COLUMN preview_duration REAL;
ALTER TABLE voices ADD COLUMN preview_error TEXT;
UPDATE voices SET clone_mode='text_conditioned' WHERE length(trim(ref_text))>0;
ALTER TABLE jobs ADD COLUMN phase TEXT NOT NULL DEFAULT 'waiting';
ALTER TABLE jobs ADD COLUMN progress INTEGER NOT NULL DEFAULT 0;
UPDATE jobs SET phase='complete',progress=100 WHERE status='completed';
