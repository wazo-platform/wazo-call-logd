CREATE TABLE public.call_log (
    id integer NOT NULL,
    date timestamp with time zone NOT NULL,
    date_answer timestamp with time zone,
    date_end timestamp with time zone,
    tenant_uuid character varying(36) NOT NULL,
    source_name character varying(255),
    source_exten character varying(255),
    source_internal_exten text,
    source_internal_context text,
    source_line_identity character varying(255),
    requested_name text,
    requested_exten character varying(255),
    requested_context character varying(255),
    requested_internal_exten text,
    requested_internal_context text,
    destination_name character varying(255),
    destination_exten character varying(255),
    destination_internal_exten text,
    destination_internal_context text,
    destination_line_identity character varying(255),
    direction character varying(255),
    user_field character varying(255),
    CONSTRAINT call_log_direction_check CHECK (((direction)::text = ANY (ARRAY[('inbound'::character varying)::text, ('internal'::character varying)::text, ('outbound'::character varying)::text])))
);
CREATE SEQUENCE public.call_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TYPE public.call_log_participant_role AS ENUM (
    'source',
    'destination'
);
CREATE TABLE public.call_log_participant (
    uuid character varying(38) NOT NULL,
    call_log_id integer,
    user_uuid character varying(38) NOT NULL,
    line_id integer,
    role public.call_log_participant_role NOT NULL,
    tags character varying(128)[] DEFAULT '{}'::character varying[] NOT NULL,
    answered boolean DEFAULT false NOT NULL
);

ALTER TABLE ONLY public.call_log ALTER COLUMN id SET DEFAULT nextval('public.call_log_id_seq'::regclass);
SELECT pg_catalog.setval('public.call_log_id_seq', 1, true);
ALTER TABLE ONLY public.call_log_participant ADD CONSTRAINT call_log_participant_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY public.call_log ADD CONSTRAINT call_log_pkey PRIMARY KEY (id);
CREATE INDEX call_log_participant__idx__user_uuid ON public.call_log_participant USING btree (user_uuid);
ALTER TABLE ONLY public.call_log_participant ADD CONSTRAINT fk_call_log_id FOREIGN KEY (call_log_id) REFERENCES public.call_log(id) ON DELETE CASCADE;
