--
-- PostgreSQL database dump
--

\restrict RTTtMwbBhedXQaJGVCrLLlkiAwfIOstgEPWtRyfgESOrfQUryUSqpZa19vcuQ3P

-- Dumped from database version 16.15 (Debian 16.15-1.pgdg12+2)
-- Dumped by pg_dump version 16.15 (Debian 16.15-1.pgdg12+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: chunk; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chunk (
    id integer NOT NULL,
    documento_id integer NOT NULL,
    contenido text,
    pagina integer,
    embedding public.vector(384),
    creado timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: chunk_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chunk_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chunk_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chunk_id_seq OWNED BY public.chunk.id;


--
-- Name: convocatoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.convocatoria (
    id integer NOT NULL,
    titulo text,
    institucion text,
    estado text,
    fecha_apertura date,
    fecha_cierre date,
    descripcion text,
    beneficiarios text,
    requisitos text,
    financiamiento text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    fuente text
);


--
-- Name: convocatoria_2; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.convocatoria_2 (
    id integer NOT NULL,
    titulo text,
    institucion text,
    estado text,
    fecha_apertura date,
    fecha_cierre date,
    descripcion text,
    beneficiarios text,
    requisitos text,
    financiamiento text,
    creado timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: convocatoria_2_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.convocatoria_2_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: convocatoria_2_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.convocatoria_2_id_seq OWNED BY public.convocatoria_2.id;


--
-- Name: convocatoria_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.convocatoria_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: convocatoria_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.convocatoria_id_seq OWNED BY public.convocatoria.id;


--
-- Name: convocatoria_seguimiento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.convocatoria_seguimiento (
    convocatoria_id integer NOT NULL,
    datos jsonb NOT NULL,
    apertura_notificada boolean DEFAULT false NOT NULL,
    actualizado timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: dato_proyecto_validado; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dato_proyecto_validado (
    id integer NOT NULL,
    usuario_sub text NOT NULL,
    campo_clave text NOT NULL,
    campo text NOT NULL,
    valor text NOT NULL,
    respuesta_ia text,
    editado_por_usuario boolean DEFAULT false NOT NULL,
    job_id integer,
    veces_confirmado integer DEFAULT 1 NOT NULL,
    actualizado timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: dato_proyecto_validado_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.dato_proyecto_validado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dato_proyecto_validado_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.dato_proyecto_validado_id_seq OWNED BY public.dato_proyecto_validado.id;


--
-- Name: documento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento (
    id integer NOT NULL,
    convocatoria_id integer NOT NULL,
    nombre text,
    url text,
    creado timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: documento_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_id_seq OWNED BY public.documento.id;


--
-- Name: evento_uso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evento_uso (
    id bigint NOT NULL,
    tipo text NOT NULL,
    usuario_sub text,
    creado timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: evento_uso_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.evento_uso_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evento_uso_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.evento_uso_id_seq OWNED BY public.evento_uso.id;


--
-- Name: formulario_job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.formulario_job (
    id integer NOT NULL,
    estado text NOT NULL,
    formulario_path text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    iniciado timestamp with time zone,
    finalizado timestamp with time zone,
    resultado_path text,
    error text,
    usuario_sub text,
    consulta_token text,
    validado_en timestamp with time zone,
    formulario_ande_id integer
);


--
-- Name: formulario_job_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.formulario_job_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: formulario_job_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.formulario_job_id_seq OWNED BY public.formulario_job.id;


--
-- Name: formularios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.formularios (
    id integer NOT NULL,
    convocatoria text NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: formularios_campos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.formularios_campos (
    id integer NOT NULL,
    formulario_id integer NOT NULL,
    orden integer NOT NULL,
    seccion text NOT NULL,
    etiqueta text NOT NULL,
    tipo text NOT NULL,
    requerido boolean DEFAULT false NOT NULL,
    opciones jsonb DEFAULT '[]'::jsonb NOT NULL,
    selector text NOT NULL,
    depende_de text,
    opciones_por_valor jsonb DEFAULT '{}'::jsonb NOT NULL,
    columnas jsonb DEFAULT '[]'::jsonb NOT NULL,
    detalle text DEFAULT ''::text NOT NULL
);


--
-- Name: formularios_campos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.formularios_campos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: formularios_campos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.formularios_campos_id_seq OWNED BY public.formularios_campos.id;


--
-- Name: formularios_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.formularios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: formularios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.formularios_id_seq OWNED BY public.formularios.id;


--
-- Name: investigadores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.investigadores (
    id integer NOT NULL,
    nombre text,
    apellido text,
    institucion text,
    titulo text,
    investigaciones text,
    nivel_sni text,
    categoria_sni text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    fuente text
);


--
-- Name: investigadores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.investigadores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: investigadores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.investigadores_id_seq OWNED BY public.investigadores.id;


--
-- Name: notificacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notificacion (
    id integer NOT NULL,
    usuario_sub text NOT NULL,
    tipo text NOT NULL,
    convocatoria_id integer,
    titulo text NOT NULL,
    mensaje text NOT NULL,
    detalle jsonb,
    clave_dedup text NOT NULL,
    leida boolean DEFAULT false NOT NULL,
    eliminada boolean DEFAULT false NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    email_enviado_en timestamp with time zone,
    email_intentos integer DEFAULT 0 NOT NULL,
    email_error text,
    CONSTRAINT notificacion_tipo_check CHECK ((tipo = ANY (ARRAY['apertura'::text, 'cierre'::text, 'actualizacion'::text])))
);


--
-- Name: notificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notificacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notificacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notificacion_id_seq OWNED BY public.notificacion.id;


--
-- Name: preferencia_notificacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.preferencia_notificacion (
    usuario_sub text NOT NULL,
    alerta_apertura boolean DEFAULT true NOT NULL,
    alerta_cierre boolean DEFAULT true NOT NULL,
    alerta_actualizacion boolean DEFAULT true NOT NULL,
    dias_anticipacion_cierre integer DEFAULT 7 NOT NULL,
    email_habilitado boolean DEFAULT false NOT NULL,
    email_habilitado_desde timestamp with time zone,
    email text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    actualizado timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT preferencia_notificacion_dias_anticipacion_cierre_check CHECK (((dias_anticipacion_cierre >= 1) AND (dias_anticipacion_cierre <= 60)))
);


--
-- Name: proyectos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proyectos (
    id integer NOT NULL,
    nombre text,
    estado text,
    anio text,
    descripcion text,
    investigadores text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    codigo text,
    fuente text,
    beneficiario text,
    instrumento text,
    sector text,
    area text,
    subsidio text,
    fecha_inicio text,
    duracion text,
    fase text
);


--
-- Name: proyectos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.proyectos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: proyectos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.proyectos_id_seq OWNED BY public.proyectos.id;


--
-- Name: relacionar_conversacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.relacionar_conversacion (
    id integer NOT NULL,
    usuario_sub text NOT NULL,
    estado text NOT NULL,
    error text,
    documentos text[] DEFAULT '{}'::text[] NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    listo timestamp with time zone,
    etapa text
);


--
-- Name: relacionar_conversacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.relacionar_conversacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: relacionar_conversacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.relacionar_conversacion_id_seq OWNED BY public.relacionar_conversacion.id;


--
-- Name: relacionar_mensaje; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.relacionar_mensaje (
    id integer NOT NULL,
    conversacion_id integer NOT NULL,
    rol text NOT NULL,
    contenido text NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    fondos jsonb
);


--
-- Name: relacionar_mensaje_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.relacionar_mensaje_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: relacionar_mensaje_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.relacionar_mensaje_id_seq OWNED BY public.relacionar_mensaje.id;


--
-- Name: respuesta_formulario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.respuesta_formulario (
    id integer NOT NULL,
    job_id integer NOT NULL,
    campo text NOT NULL,
    respuesta text,
    fuentes text,
    tipo text,
    pagina integer,
    respuesta_ia text,
    editada boolean DEFAULT false NOT NULL
);


--
-- Name: respuesta_formulario_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.respuesta_formulario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: respuesta_formulario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.respuesta_formulario_id_seq OWNED BY public.respuesta_formulario.id;


--
-- Name: suscripcion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.suscripcion (
    id integer NOT NULL,
    usuario_sub text NOT NULL,
    tipo text NOT NULL,
    convocatoria_id integer,
    valor text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT suscripcion_tipo_check CHECK ((tipo = ANY (ARRAY['convocatoria'::text, 'institucion'::text, 'tematica'::text])))
);


--
-- Name: suscripcion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.suscripcion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: suscripcion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.suscripcion_id_seq OWNED BY public.suscripcion.id;


--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuarios (
    id integer NOT NULL,
    keycloak_id text NOT NULL,
    email text,
    nombre text,
    apellido text,
    celular text,
    departamento_residencia text,
    departamentos_actuacion text[] DEFAULT '{}'::text[] NOT NULL,
    instituciones text[] DEFAULT '{}'::text[] NOT NULL,
    perfil text,
    perfil_otro text,
    rol text,
    estado text DEFAULT 'pendiente'::text NOT NULL,
    revisado_por text,
    revisado_en timestamp with time zone,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    actualizado timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: usuarios_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuarios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuarios_id_seq OWNED BY public.usuarios.id;


--
-- Name: chunk id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunk ALTER COLUMN id SET DEFAULT nextval('public.chunk_id_seq'::regclass);


--
-- Name: convocatoria id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convocatoria ALTER COLUMN id SET DEFAULT nextval('public.convocatoria_id_seq'::regclass);


--
-- Name: convocatoria_2 id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convocatoria_2 ALTER COLUMN id SET DEFAULT nextval('public.convocatoria_2_id_seq'::regclass);


--
-- Name: dato_proyecto_validado id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dato_proyecto_validado ALTER COLUMN id SET DEFAULT nextval('public.dato_proyecto_validado_id_seq'::regclass);


--
-- Name: documento id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento ALTER COLUMN id SET DEFAULT nextval('public.documento_id_seq'::regclass);


--
-- Name: evento_uso id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_uso ALTER COLUMN id SET DEFAULT nextval('public.evento_uso_id_seq'::regclass);


--
-- Name: formulario_job id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formulario_job ALTER COLUMN id SET DEFAULT nextval('public.formulario_job_id_seq'::regclass);


--
-- Name: formularios id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formularios ALTER COLUMN id SET DEFAULT nextval('public.formularios_id_seq'::regclass);


--
-- Name: formularios_campos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formularios_campos ALTER COLUMN id SET DEFAULT nextval('public.formularios_campos_id_seq'::regclass);


--
-- Name: investigadores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.investigadores ALTER COLUMN id SET DEFAULT nextval('public.investigadores_id_seq'::regclass);


--
-- Name: notificacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion ALTER COLUMN id SET DEFAULT nextval('public.notificacion_id_seq'::regclass);


--
-- Name: proyectos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyectos ALTER COLUMN id SET DEFAULT nextval('public.proyectos_id_seq'::regclass);


--
-- Name: relacionar_conversacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacionar_conversacion ALTER COLUMN id SET DEFAULT nextval('public.relacionar_conversacion_id_seq'::regclass);


--
-- Name: relacionar_mensaje id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacionar_mensaje ALTER COLUMN id SET DEFAULT nextval('public.relacionar_mensaje_id_seq'::regclass);


--
-- Name: respuesta_formulario id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.respuesta_formulario ALTER COLUMN id SET DEFAULT nextval('public.respuesta_formulario_id_seq'::regclass);


--
-- Name: suscripcion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suscripcion ALTER COLUMN id SET DEFAULT nextval('public.suscripcion_id_seq'::regclass);


--
-- Name: usuarios id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios ALTER COLUMN id SET DEFAULT nextval('public.usuarios_id_seq'::regclass);


--
-- Name: chunk chunk_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunk
    ADD CONSTRAINT chunk_pkey PRIMARY KEY (id);


--
-- Name: convocatoria_2 convocatoria_2_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convocatoria_2
    ADD CONSTRAINT convocatoria_2_pkey PRIMARY KEY (id);


--
-- Name: convocatoria convocatoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convocatoria
    ADD CONSTRAINT convocatoria_pkey PRIMARY KEY (id);


--
-- Name: convocatoria_seguimiento convocatoria_seguimiento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convocatoria_seguimiento
    ADD CONSTRAINT convocatoria_seguimiento_pkey PRIMARY KEY (convocatoria_id);


--
-- Name: dato_proyecto_validado dato_proyecto_validado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dato_proyecto_validado
    ADD CONSTRAINT dato_proyecto_validado_pkey PRIMARY KEY (id);


--
-- Name: dato_proyecto_validado dato_proyecto_validado_usuario_sub_campo_clave_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dato_proyecto_validado
    ADD CONSTRAINT dato_proyecto_validado_usuario_sub_campo_clave_key UNIQUE (usuario_sub, campo_clave);


--
-- Name: documento documento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento
    ADD CONSTRAINT documento_pkey PRIMARY KEY (id);


--
-- Name: evento_uso evento_uso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_uso
    ADD CONSTRAINT evento_uso_pkey PRIMARY KEY (id);


--
-- Name: formulario_job formulario_job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formulario_job
    ADD CONSTRAINT formulario_job_pkey PRIMARY KEY (id);


--
-- Name: formularios_campos formularios_campos_formulario_id_orden_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formularios_campos
    ADD CONSTRAINT formularios_campos_formulario_id_orden_key UNIQUE (formulario_id, orden);


--
-- Name: formularios_campos formularios_campos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formularios_campos
    ADD CONSTRAINT formularios_campos_pkey PRIMARY KEY (id);


--
-- Name: formularios formularios_convocatoria_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formularios
    ADD CONSTRAINT formularios_convocatoria_key UNIQUE (convocatoria);


--
-- Name: formularios formularios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formularios
    ADD CONSTRAINT formularios_pkey PRIMARY KEY (id);


--
-- Name: investigadores investigadores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.investigadores
    ADD CONSTRAINT investigadores_pkey PRIMARY KEY (id);


--
-- Name: notificacion notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_pkey PRIMARY KEY (id);


--
-- Name: notificacion notificacion_usuario_sub_clave_dedup_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_usuario_sub_clave_dedup_key UNIQUE (usuario_sub, clave_dedup);


--
-- Name: preferencia_notificacion preferencia_notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preferencia_notificacion
    ADD CONSTRAINT preferencia_notificacion_pkey PRIMARY KEY (usuario_sub);


--
-- Name: proyectos proyectos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyectos
    ADD CONSTRAINT proyectos_pkey PRIMARY KEY (id);


--
-- Name: relacionar_conversacion relacionar_conversacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacionar_conversacion
    ADD CONSTRAINT relacionar_conversacion_pkey PRIMARY KEY (id);


--
-- Name: relacionar_mensaje relacionar_mensaje_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacionar_mensaje
    ADD CONSTRAINT relacionar_mensaje_pkey PRIMARY KEY (id);


--
-- Name: respuesta_formulario respuesta_formulario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.respuesta_formulario
    ADD CONSTRAINT respuesta_formulario_pkey PRIMARY KEY (id);


--
-- Name: suscripcion suscripcion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suscripcion
    ADD CONSTRAINT suscripcion_pkey PRIMARY KEY (id);


--
-- Name: usuarios usuarios_keycloak_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_keycloak_id_key UNIQUE (keycloak_id);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: evento_uso_creado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX evento_uso_creado ON public.evento_uso USING btree (creado);


--
-- Name: evento_uso_tipo_creado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX evento_uso_tipo_creado ON public.evento_uso USING btree (tipo, creado);


--
-- Name: notificacion_por_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX notificacion_por_usuario ON public.notificacion USING btree (usuario_sub, eliminada, creado DESC);


--
-- Name: proyectos_fuente_unica; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX proyectos_fuente_unica ON public.proyectos USING btree (fuente);


--
-- Name: suscripcion_por_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX suscripcion_por_usuario ON public.suscripcion USING btree (usuario_sub);


--
-- Name: suscripcion_unica; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX suscripcion_unica ON public.suscripcion USING btree (usuario_sub, tipo, COALESCE(convocatoria_id, 0), COALESCE(lower(valor), ''::text));


--
-- Name: chunk chunk_documento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunk
    ADD CONSTRAINT chunk_documento_id_fkey FOREIGN KEY (documento_id) REFERENCES public.documento(id);


--
-- Name: dato_proyecto_validado dato_proyecto_validado_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dato_proyecto_validado
    ADD CONSTRAINT dato_proyecto_validado_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.formulario_job(id) ON DELETE SET NULL;


--
-- Name: documento documento_convocatoria_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento
    ADD CONSTRAINT documento_convocatoria_id_fkey FOREIGN KEY (convocatoria_id) REFERENCES public.convocatoria(id);


--
-- Name: formulario_job formulario_job_formulario_ande_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formulario_job
    ADD CONSTRAINT formulario_job_formulario_ande_id_fkey FOREIGN KEY (formulario_ande_id) REFERENCES public.formularios(id);


--
-- Name: formularios_campos formularios_campos_formulario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formularios_campos
    ADD CONSTRAINT formularios_campos_formulario_id_fkey FOREIGN KEY (formulario_id) REFERENCES public.formularios(id) ON DELETE CASCADE;


--
-- Name: relacionar_mensaje relacionar_mensaje_conversacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacionar_mensaje
    ADD CONSTRAINT relacionar_mensaje_conversacion_id_fkey FOREIGN KEY (conversacion_id) REFERENCES public.relacionar_conversacion(id) ON DELETE CASCADE;


--
-- Name: respuesta_formulario respuesta_formulario_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.respuesta_formulario
    ADD CONSTRAINT respuesta_formulario_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.formulario_job(id);


--
-- PostgreSQL database dump complete
--

\unrestrict RTTtMwbBhedXQaJGVCrLLlkiAwfIOstgEPWtRyfgESOrfQUryUSqpZa19vcuQ3P

