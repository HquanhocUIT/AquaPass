begin;

-- Stable ID keeps the demo relationships reproducible.
insert into public.incidents (
    id,
    title,
    description,
    incident_type,
    location_name,
    latitude,
    longitude,
    severity,
    status,
    occurred_at
)
values (
    '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8',
    'Fish mortality at urban freshwater site',
    'SIMULATED DATA: Multiple dead fish were reported after heavy rainfall.',
    'FISH_MORTALITY',
    'Demo Urban Lake - Site A',
    10.7769,
    106.7009,
    'HIGH',
    'OPEN',
    now() - interval '1 hour'
)
on conflict (id) do nothing;

-- Each evidence item is inserted only if its code is not present yet.
insert into public.evidence (
    id, incident_id, code, evidence_type, state, value_text,
    source, observed_at, reliability_score, provenance, is_simulated
)
select
    '00000000-0000-4000-8000-000000000101',
    '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8',
    'FISH_MORTALITY_REPORT',
    'FIELD_REPORT',
    'KNOWN',
    'Multiple dead fish observed near the shoreline',
    'Simulated citizen report',
    now() - interval '55 minutes',
    0.65,
    '{"simulated": true, "reporter_type": "citizen"}'::jsonb,
    true
where not exists (
    select 1 from public.evidence
    where incident_id = '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8'
      and code = 'FISH_MORTALITY_REPORT'
);

insert into public.evidence (
    id, incident_id, code, evidence_type, state, value_numeric, unit,
    source, observed_at, reliability_score, provenance, is_simulated
)
select
    '00000000-0000-4000-8000-000000000102',
    '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8',
    'DISSOLVED_OXYGEN_SENSOR',
    'SENSOR_READING',
    'LOW_CONFIDENCE',
    3.8,
    'mg/L',
    'Simulated fixed sensor',
    now() - interval '3 hours',
    0.55,
    '{"simulated": true, "quality_note": "requires field verification"}'::jsonb,
    true
where not exists (
    select 1 from public.evidence
    where incident_id = '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8'
      and code = 'DISSOLVED_OXYGEN_SENSOR'
);

insert into public.evidence (
    id, incident_id, code, evidence_type, state, value_numeric, unit,
    source, observed_at, reliability_score, provenance, is_simulated
)
select
    '00000000-0000-4000-8000-000000000103',
    '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8',
    'HEAVY_RAINFALL',
    'WEATHER_OBSERVATION',
    'KNOWN',
    42.0,
    'mm/24h',
    'Simulated weather service',
    now() - interval '6 hours',
    0.90,
    '{"simulated": true}'::jsonb,
    true
where not exists (
    select 1 from public.evidence
    where incident_id = '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8'
      and code = 'HEAVY_RAINFALL'
);

-- Initial pending decision for the fish-mortality incident.
insert into public.decisions (
    id,
    incident_id,
    question,
    deadline,
    status,
    current_version
)
values (
    '00000000-0000-4000-8000-000000000201',
    '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8',
    'Should the authority escalate the field investigation?',
    now() + interval '2 hours',
    'PENDING',
    1
)
on conflict (id) do nothing;

-- Version 1 captures the evidence available before field verification.
insert into public.decision_versions (
    id,
    decision_id,
    version_number,
    summary,
    uncertainty_level,
    evidence_snapshot,
    approval_status,
    created_by
)
values (
    '00000000-0000-4000-8000-000000000301',
    '00000000-0000-4000-8000-000000000201',
    1,
    'Current evidence is insufficient; field verification is pending.',
    'HIGH',
    (
        select jsonb_build_object(
            'evidence_ids',
            coalesce(jsonb_agg(id order by observed_at), '[]'::jsonb),
            'evidence_codes',
            coalesce(jsonb_agg(code order by observed_at), '[]'::jsonb)
        )
        from public.evidence
        where incident_id = '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8'
    ),
    'PENDING',
    'demo-seed'
)
on conflict (decision_id, version_number) do nothing;

-- Supporting records for the next-request demonstration. No request is created
-- by the seed: a human must confirm it in the workflow.
insert into public.hypotheses (
    id, incident_id, code, title, description, status, support_score
) values
    (
        '00000000-0000-4000-8000-000000000601',
        '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8',
        'H1', 'Low dissolved oxygen',
        'SIMULATED: runoff may have contributed to oxygen depletion.',
        'ACTIVE', 0.6
    ),
    (
        '00000000-0000-4000-8000-000000000602',
        '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8',
        'H2', 'Toxic discharge',
        'SIMULATED: an unverified discharge is another possible explanation.',
        'ACTIVE', 0.4
    )
on conflict (id) do nothing;

insert into public.actors (
    id, code, name, actor_type, capabilities, location_name,
    available, capacity, turnaround_minutes
) values (
    '00000000-0000-4000-8000-000000000401',
    'DEMO_FIELD_TEAM',
    'Simulated field team',
    'FIELD_TEAM',
    '["FIELD_DISSOLVED_OXYGEN"]'::jsonb,
    'Demo Urban Lake - Site A',
    true, 1, 20
)
on conflict (id) do nothing;

insert into public.evidence_gaps (
    id, incident_id, decision_id, code, description, criticality, status, rationale
) values (
    '00000000-0000-4000-8000-000000000501',
    '8f03fdce-cc4e-4fc1-a90b-15b2122e68b8',
    '00000000-0000-4000-8000-000000000201',
    'FIELD_DISSOLVED_OXYGEN',
    'A recent field dissolved-oxygen measurement is missing.',
    'HIGH', 'OPEN',
    'The earlier sensor reading has low confidence and requires verification.'
)
on conflict (id) do nothing;

commit;
