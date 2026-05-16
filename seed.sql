-- Decipher seed data (minimum viable: archetype taxonomies, industries,
-- one operator, brand-voice scaffold). Master 47 questions added in M3
-- from docs/master_questions.csv.

-- D-006: default taxonomy = 4 (Source A). Taxonomy 2 placeholder for 8 (Source B).
INSERT INTO archetype_taxonomies (taxonomy_id, name, description, is_active) VALUES
    (1, 'Source A: 4 EQ Identities',
     'Regulator, Edge-Builder, Observer, Labeler. Plurality vote on 3 flagged questions.',
     TRUE),
    (2, 'Source B: 8 personas',
     '8-archetype taxonomy from Steve''s executive dashboard mockup. Placeholder until Steve confirms.',
     FALSE)
ON CONFLICT (taxonomy_id) DO NOTHING;

INSERT INTO archetypes (taxonomy_id, code, name, description) VALUES
    (1, 'regulator',    'Regulator',    'Composed, methodical, slow to react.'),
    (1, 'edge_builder', 'Edge-Builder', 'Challenger; frames the conversation; leans in.'),
    (1, 'observer',     'Observer',     'Analytical; listens long; intervenes precisely.'),
    (1, 'labeler',      'Labeler',      'Names what is happening in the room, NVC-style.'),
    (2, 'strategic_empath',     'Strategic Empath',     'Placeholder.'),
    (2, 'trust_architect',      'Trust Architect',      'Placeholder.'),
    (2, 'confident_storyteller','Confident Storyteller','Placeholder.'),
    (2, 'story_listener',       'Story Listener',       'Placeholder.'),
    (2, 'elite_operator',       'Elite Operator',       'Placeholder.'),
    (2, 'calm_diagnostician',   'Calm Diagnostician',   'Placeholder.'),
    (2, 'composed_reader',      'Composed Reader',      'Placeholder.'),
    (2, 'raw_material',         'Raw Material',         'Placeholder.')
ON CONFLICT (taxonomy_id, code) DO NOTHING;

INSERT INTO industries (code, name, description) VALUES
    ('media',      'Media',      'Advertising, publishing, content.'),
    ('pharma',     'Pharma',     'Pharmaceutical and life sciences.'),
    ('automotive', 'Automotive', 'OEM, fleet, dealer networks.'),
    ('tech',       'Tech',       'B2B SaaS, infrastructure, services.')
ON CONFLICT (code) DO NOTHING;

INSERT INTO audit_versions (code, name) VALUES
    ('master_v1', 'Decipher DNA Audit (master v1)')
ON CONFLICT (code) DO NOTHING;

-- Operator: Steve (single sole operator)
INSERT INTO respondents (email, name, role) VALUES
    ('steve@decipher.com.au', 'Steve', 'operator')
ON CONFLICT (email) DO NOTHING;

-- Brand voice scaffold (M10 will replace via Squarespace exporter)
INSERT INTO brand_voice (id, voice_md) VALUES (
    1,
    E'# Decipher brand voice\n\n## Do\n- Diagnose before prescribe.\n- Plain Australian English. Short sentences.\n- Name the cost of the gap, then the intervention.\n\n## Don''t\n- No bro-sales clichés (close, crush, killer).\n- No AI filler (unlock, elevate, seamless, delve, leverage, tapestry).\n- No em dashes anywhere.\n\n## Signature phrases\n- "Diagnose before prescribe."\n- "As soon as someone feels understood, they will buy from you continuously."\n- "Not always-be-closing. Always-be-understanding."\n'
) ON CONFLICT (id) DO UPDATE SET voice_md = EXCLUDED.voice_md, updated_at = now();
