--
-- PostgreSQL database dump
--

\restrict clDmz6pNT1V4BIcZ2OK3QWEukyiuAC3CMrqZhSBHH3XiQhRazBShag5Fk8fo6wh

-- Dumped from database version 18.1 (Debian 18.1-1.pgdg13+2)
-- Dumped by pg_dump version 18.1 (Debian 18.1-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: adjustment; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.adjustment (
    id integer NOT NULL,
    location_id integer,
    product_id integer,
    delta numeric(18,6) NOT NULL,
    unit_code character varying(32),
    reason character varying(255),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.adjustment OWNER TO cavina;

--
-- Name: TABLE adjustment; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.adjustment IS 'Adjustments table';


--
-- Name: adjustment_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.adjustment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.adjustment_id_seq OWNER TO cavina;

--
-- Name: adjustment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.adjustment_id_seq OWNED BY public.adjustment.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO cavina;

--
-- Name: attribute_definition; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.attribute_definition (
    id integer NOT NULL,
    product_type_id integer NOT NULL,
    name character varying(128) NOT NULL,
    code character varying(64) NOT NULL,
    data_type character varying(16) NOT NULL,
    unit_code character varying(32),
    is_required boolean DEFAULT false NOT NULL
);


ALTER TABLE public.attribute_definition OWNER TO cavina;

--
-- Name: TABLE attribute_definition; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.attribute_definition IS 'Attribute definitions per product type';


--
-- Name: attribute_definition_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.attribute_definition_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attribute_definition_id_seq OWNER TO cavina;

--
-- Name: attribute_definition_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.attribute_definition_id_seq OWNED BY public.attribute_definition.id;


--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.audit_log (
    id integer CONSTRAINT auditlog_id_not_null NOT NULL,
    model character varying(128),
    record_id character varying(128),
    action character varying(16),
    old_data json,
    new_data json,
    actor character varying(128),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.audit_log OWNER TO cavina;

--
-- Name: TABLE audit_log; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.audit_log IS 'Audit log table';


--
-- Name: auditlog_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.auditlog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.auditlog_id_seq OWNER TO cavina;

--
-- Name: auditlog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.auditlog_id_seq OWNED BY public.audit_log.id;


--
-- Name: composite_component; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.composite_component (
    id integer CONSTRAINT compositecomponent_id_not_null NOT NULL,
    parent_product_id integer,
    component_product_id integer,
    quantity numeric(18,6) CONSTRAINT compositecomponent_quantity_not_null NOT NULL,
    unit_code character varying(32),
    substitution_allowed boolean DEFAULT false CONSTRAINT compositecomponent_substitution_allowed_not_null NOT NULL,
    rounding character varying(32)
);


ALTER TABLE public.composite_component OWNER TO cavina;

--
-- Name: TABLE composite_component; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.composite_component IS 'Composite components table';


--
-- Name: compositecomponent_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.compositecomponent_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.compositecomponent_id_seq OWNER TO cavina;

--
-- Name: compositecomponent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.compositecomponent_id_seq OWNED BY public.composite_component.id;


--
-- Name: inventory_snapshot; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.inventory_snapshot (
    id integer CONSTRAINT inventorysnapshot_id_not_null NOT NULL,
    location_id integer,
    taken_at timestamp without time zone DEFAULT now(),
    data json CONSTRAINT inventorysnapshot_data_not_null NOT NULL
);


ALTER TABLE public.inventory_snapshot OWNER TO cavina;

--
-- Name: TABLE inventory_snapshot; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.inventory_snapshot IS 'Inventory snapshots table';


--
-- Name: inventorysnapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.inventorysnapshot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inventorysnapshot_id_seq OWNER TO cavina;

--
-- Name: inventorysnapshot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.inventorysnapshot_id_seq OWNED BY public.inventory_snapshot.id;


--
-- Name: location; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.location (
    id integer NOT NULL,
    name character varying(128),
    kind character varying(64) NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.location OWNER TO cavina;

--
-- Name: TABLE location; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.location IS 'Location table';


--
-- Name: location_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.location_id_seq OWNER TO cavina;

--
-- Name: location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.location_id_seq OWNED BY public.location.id;


--
-- Name: permission; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.permission (
    id integer NOT NULL,
    code character varying(128),
    description character varying(255)
);


ALTER TABLE public.permission OWNER TO cavina;

--
-- Name: TABLE permission; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.permission IS 'Permissions table';


--
-- Name: permission_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.permission_id_seq OWNER TO cavina;

--
-- Name: permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.permission_id_seq OWNED BY public.permission.id;


--
-- Name: price_list; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.price_list (
    id integer CONSTRAINT pricelist_id_not_null NOT NULL,
    location_id integer,
    product_id integer,
    unit_code character varying(32),
    currency character varying(3) CONSTRAINT pricelist_currency_not_null NOT NULL,
    amount numeric(18,2) CONSTRAINT pricelist_amount_not_null NOT NULL
);


ALTER TABLE public.price_list OWNER TO cavina;

--
-- Name: TABLE price_list; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.price_list IS 'Price list table';


--
-- Name: pricelist_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.pricelist_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pricelist_id_seq OWNER TO cavina;

--
-- Name: pricelist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.pricelist_id_seq OWNED BY public.price_list.id;


--
-- Name: product; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.product (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    sku character varying(64),
    primary_category character varying(64) NOT NULL,
    product_type_id integer,
    base_unit_code character varying(32),
    is_composite boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    tax_flags character varying(128),
    unit_cost numeric(18,2) DEFAULT '0'::numeric NOT NULL
);


ALTER TABLE public.product OWNER TO cavina;

--
-- Name: TABLE product; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.product IS 'Product table';


--
-- Name: product_attribute; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.product_attribute (
    id integer CONSTRAINT productattribute_id_not_null NOT NULL,
    product_id integer,
    name character varying(64) CONSTRAINT productattribute_name_not_null NOT NULL,
    value character varying(255) CONSTRAINT productattribute_value_not_null NOT NULL
);


ALTER TABLE public.product_attribute OWNER TO cavina;

--
-- Name: TABLE product_attribute; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.product_attribute IS 'Product attributes table';


--
-- Name: product_attribute_value; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.product_attribute_value (
    product_id integer NOT NULL,
    attribute_definition_id integer NOT NULL,
    value_number numeric(18,6),
    value_boolean boolean,
    value_string character varying(255)
);


ALTER TABLE public.product_attribute_value OWNER TO cavina;

--
-- Name: TABLE product_attribute_value; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.product_attribute_value IS 'Typed attribute values per product';


--
-- Name: product_category; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.product_category (
    id integer CONSTRAINT productcategory_id_not_null NOT NULL,
    product_id integer,
    category character varying(64) CONSTRAINT productcategory_category_not_null NOT NULL
);


ALTER TABLE public.product_category OWNER TO cavina;

--
-- Name: TABLE product_category; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.product_category IS 'Product categories table';


--
-- Name: product_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.product_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.product_id_seq OWNER TO cavina;

--
-- Name: product_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.product_id_seq OWNED BY public.product.id;


--
-- Name: product_type; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.product_type (
    id integer CONSTRAINT producttype_id_not_null NOT NULL,
    name character varying(100),
    description character varying(255),
    is_composite boolean DEFAULT false NOT NULL
);


ALTER TABLE public.product_type OWNER TO cavina;

--
-- Name: TABLE product_type; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.product_type IS 'Product types table';


--
-- Name: productattribute_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.productattribute_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.productattribute_id_seq OWNER TO cavina;

--
-- Name: productattribute_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.productattribute_id_seq OWNED BY public.product_attribute.id;


--
-- Name: productcategory_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.productcategory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.productcategory_id_seq OWNER TO cavina;

--
-- Name: productcategory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.productcategory_id_seq OWNED BY public.product_category.id;


--
-- Name: producttype_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.producttype_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.producttype_id_seq OWNER TO cavina;

--
-- Name: producttype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.producttype_id_seq OWNED BY public.product_type.id;


--
-- Name: request_log; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.request_log (
    id integer CONSTRAINT requestlog_id_not_null NOT NULL,
    request_id character varying(128),
    method character varying(8),
    path character varying(255),
    status_code integer,
    user_id integer,
    terminal_id integer,
    context json,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.request_log OWNER TO cavina;

--
-- Name: TABLE request_log; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.request_log IS 'Request log table';


--
-- Name: requestlog_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.requestlog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.requestlog_id_seq OWNER TO cavina;

--
-- Name: requestlog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.requestlog_id_seq OWNED BY public.request_log.id;


--
-- Name: role; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.role (
    id integer NOT NULL,
    name character varying(64),
    scope character varying(16) DEFAULT 'global'::character varying NOT NULL,
    location_id integer
);


ALTER TABLE public.role OWNER TO cavina;

--
-- Name: TABLE role; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.role IS 'Roles table';


--
-- Name: role_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.role_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.role_id_seq OWNER TO cavina;

--
-- Name: role_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.role_id_seq OWNED BY public.role.id;


--
-- Name: role_permission; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.role_permission (
    id integer CONSTRAINT rolepermission_id_not_null NOT NULL,
    role_id integer,
    permission_id integer
);


ALTER TABLE public.role_permission OWNER TO cavina;

--
-- Name: TABLE role_permission; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.role_permission IS 'Role permissions table';


--
-- Name: rolepermission_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.rolepermission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.rolepermission_id_seq OWNER TO cavina;

--
-- Name: rolepermission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.rolepermission_id_seq OWNED BY public.role_permission.id;


--
-- Name: sale_event; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.sale_event (
    id integer CONSTRAINT saleevent_id_not_null NOT NULL,
    event_id character varying(128),
    terminal_id integer,
    location_id integer,
    payload json CONSTRAINT saleevent_payload_not_null NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying CONSTRAINT saleevent_status_not_null NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    confirmed_at timestamp without time zone
);


ALTER TABLE public.sale_event OWNER TO cavina;

--
-- Name: TABLE sale_event; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.sale_event IS 'Sale events table';


--
-- Name: sale_line; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.sale_line (
    id integer CONSTRAINT saleline_id_not_null NOT NULL,
    sale_event_id integer,
    product_id integer,
    quantity numeric(18,6) CONSTRAINT saleline_quantity_not_null NOT NULL,
    unit_code character varying(32),
    currency character varying(3) CONSTRAINT saleline_currency_not_null NOT NULL,
    price numeric(18,2) CONSTRAINT saleline_price_not_null NOT NULL
);


ALTER TABLE public.sale_line OWNER TO cavina;

--
-- Name: TABLE sale_line; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.sale_line IS 'Sale lines table';


--
-- Name: saleevent_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.saleevent_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.saleevent_id_seq OWNER TO cavina;

--
-- Name: saleevent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.saleevent_id_seq OWNED BY public.sale_event.id;


--
-- Name: saleline_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.saleline_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.saleline_id_seq OWNER TO cavina;

--
-- Name: saleline_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.saleline_id_seq OWNED BY public.sale_line.id;


--
-- Name: stock; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.stock (
    id integer NOT NULL,
    location_id integer,
    product_id integer,
    quantity numeric(18,6) DEFAULT '0'::numeric NOT NULL,
    unit_code character varying(32),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT ck_stock_non_negative CHECK ((quantity >= (0)::numeric))
);


ALTER TABLE public.stock OWNER TO cavina;

--
-- Name: TABLE stock; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.stock IS 'Stock table';


--
-- Name: stock_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.stock_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stock_id_seq OWNER TO cavina;

--
-- Name: stock_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.stock_id_seq OWNED BY public.stock.id;


--
-- Name: terminal; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.terminal (
    id integer NOT NULL,
    terminal_id character varying(64),
    location_id integer,
    secret_hash character varying(255) NOT NULL,
    status character varying(32) DEFAULT 'active'::character varying NOT NULL
);


ALTER TABLE public.terminal OWNER TO cavina;

--
-- Name: TABLE terminal; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.terminal IS 'Terminals table';


--
-- Name: terminal_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.terminal_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.terminal_id_seq OWNER TO cavina;

--
-- Name: terminal_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.terminal_id_seq OWNED BY public.terminal.id;


--
-- Name: transfer; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.transfer (
    id integer NOT NULL,
    from_location_id integer,
    to_location_id integer,
    product_id integer,
    quantity numeric(18,6) NOT NULL,
    unit_code character varying(32),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.transfer OWNER TO cavina;

--
-- Name: TABLE transfer; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.transfer IS 'Transfers table';


--
-- Name: transfer_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.transfer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transfer_id_seq OWNER TO cavina;

--
-- Name: transfer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.transfer_id_seq OWNED BY public.transfer.id;


--
-- Name: unit; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.unit (
    code character varying(32) NOT NULL,
    description character varying(255) NOT NULL,
    ratio_to_base numeric(18,6) DEFAULT '1'::numeric NOT NULL,
    discrete_step numeric(10,6)
);


ALTER TABLE public.unit OWNER TO cavina;

--
-- Name: TABLE unit; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.unit IS 'Unit table';


--
-- Name: COLUMN unit.code; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON COLUMN public.unit.code IS 'Unit code, e.g. bottle, glass';


--
-- Name: COLUMN unit.description; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON COLUMN public.unit.description IS 'Human readable description';


--
-- Name: COLUMN unit.ratio_to_base; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON COLUMN public.unit.ratio_to_base IS 'Conversion ratio to base unit for this product group';


--
-- Name: COLUMN unit.discrete_step; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON COLUMN public.unit.discrete_step IS 'Optional discrete step to control fractional quantities';


--
-- Name: unit_conversion; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.unit_conversion (
    id integer CONSTRAINT unitconversion_id_not_null NOT NULL,
    from_unit character varying(32),
    to_unit character varying(32),
    ratio numeric(18,6) CONSTRAINT unitconversion_ratio_not_null NOT NULL
);


ALTER TABLE public.unit_conversion OWNER TO cavina;

--
-- Name: TABLE unit_conversion; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.unit_conversion IS 'Unit conversions table';


--
-- Name: unitconversion_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.unitconversion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.unitconversion_id_seq OWNER TO cavina;

--
-- Name: unitconversion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.unitconversion_id_seq OWNED BY public.unit_conversion.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    username character varying(64),
    password_hash character varying(255) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_superuser boolean DEFAULT false NOT NULL
);


ALTER TABLE public."user" OWNER TO cavina;

--
-- Name: TABLE "user"; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public."user" IS 'Users table';


--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_id_seq OWNER TO cavina;

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: user_role; Type: TABLE; Schema: public; Owner: cavina
--

CREATE TABLE public.user_role (
    id integer CONSTRAINT userrole_id_not_null NOT NULL,
    user_id integer,
    role_id integer
);


ALTER TABLE public.user_role OWNER TO cavina;

--
-- Name: TABLE user_role; Type: COMMENT; Schema: public; Owner: cavina
--

COMMENT ON TABLE public.user_role IS 'User roles table';


--
-- Name: userrole_id_seq; Type: SEQUENCE; Schema: public; Owner: cavina
--

CREATE SEQUENCE public.userrole_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.userrole_id_seq OWNER TO cavina;

--
-- Name: userrole_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cavina
--

ALTER SEQUENCE public.userrole_id_seq OWNED BY public.user_role.id;


--
-- Name: adjustment id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.adjustment ALTER COLUMN id SET DEFAULT nextval('public.adjustment_id_seq'::regclass);


--
-- Name: attribute_definition id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.attribute_definition ALTER COLUMN id SET DEFAULT nextval('public.attribute_definition_id_seq'::regclass);


--
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.auditlog_id_seq'::regclass);


--
-- Name: composite_component id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.composite_component ALTER COLUMN id SET DEFAULT nextval('public.compositecomponent_id_seq'::regclass);


--
-- Name: inventory_snapshot id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.inventory_snapshot ALTER COLUMN id SET DEFAULT nextval('public.inventorysnapshot_id_seq'::regclass);


--
-- Name: location id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.location ALTER COLUMN id SET DEFAULT nextval('public.location_id_seq'::regclass);


--
-- Name: permission id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.permission ALTER COLUMN id SET DEFAULT nextval('public.permission_id_seq'::regclass);


--
-- Name: price_list id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.price_list ALTER COLUMN id SET DEFAULT nextval('public.pricelist_id_seq'::regclass);


--
-- Name: product id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product ALTER COLUMN id SET DEFAULT nextval('public.product_id_seq'::regclass);


--
-- Name: product_attribute id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_attribute ALTER COLUMN id SET DEFAULT nextval('public.productattribute_id_seq'::regclass);


--
-- Name: product_category id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_category ALTER COLUMN id SET DEFAULT nextval('public.productcategory_id_seq'::regclass);


--
-- Name: product_type id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_type ALTER COLUMN id SET DEFAULT nextval('public.producttype_id_seq'::regclass);


--
-- Name: request_log id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.request_log ALTER COLUMN id SET DEFAULT nextval('public.requestlog_id_seq'::regclass);


--
-- Name: role id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.role ALTER COLUMN id SET DEFAULT nextval('public.role_id_seq'::regclass);


--
-- Name: role_permission id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.role_permission ALTER COLUMN id SET DEFAULT nextval('public.rolepermission_id_seq'::regclass);


--
-- Name: sale_event id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.sale_event ALTER COLUMN id SET DEFAULT nextval('public.saleevent_id_seq'::regclass);


--
-- Name: sale_line id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.sale_line ALTER COLUMN id SET DEFAULT nextval('public.saleline_id_seq'::regclass);


--
-- Name: stock id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.stock ALTER COLUMN id SET DEFAULT nextval('public.stock_id_seq'::regclass);


--
-- Name: terminal id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.terminal ALTER COLUMN id SET DEFAULT nextval('public.terminal_id_seq'::regclass);


--
-- Name: transfer id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.transfer ALTER COLUMN id SET DEFAULT nextval('public.transfer_id_seq'::regclass);


--
-- Name: unit_conversion id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.unit_conversion ALTER COLUMN id SET DEFAULT nextval('public.unitconversion_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Name: user_role id; Type: DEFAULT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.user_role ALTER COLUMN id SET DEFAULT nextval('public.userrole_id_seq'::regclass);


--
-- Data for Name: adjustment; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.adjustment (id, location_id, product_id, delta, unit_code, reason, created_at) VALUES (1, 1, 1, 1.000000, 'bottle', 'Initial count', '2026-01-21 10:46:12.009953');
INSERT INTO public.adjustment (id, location_id, product_id, delta, unit_code, reason, created_at) VALUES (2, 3, 7, 1.000000, 'bottle', 'Initial count', '2026-01-21 18:07:43.418027');


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.alembic_version (version_num) VALUES ('0002_simple_catalog');


--
-- Data for Name: attribute_definition; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.attribute_definition (id, product_type_id, name, code, data_type, unit_code, is_required) VALUES (1, 4, 'Объём', 'volume', 'number', 'liter', true);
INSERT INTO public.attribute_definition (id, product_type_id, name, code, data_type, unit_code, is_required) VALUES (2, 4, 'Крепость', 'strength', 'number', NULL, true);
INSERT INTO public.attribute_definition (id, product_type_id, name, code, data_type, unit_code, is_required) VALUES (3, 4, 'Стаканов из бутылки', 'glasses_per_bottle', 'number', NULL, false);
INSERT INTO public.attribute_definition (id, product_type_id, name, code, data_type, unit_code, is_required) VALUES (4, 5, 'Вес', 'weight', 'number', 'kg', true);
INSERT INTO public.attribute_definition (id, product_type_id, name, code, data_type, unit_code, is_required) VALUES (5, 5, 'Калорийность', 'calories', 'number', NULL, true);
INSERT INTO public.attribute_definition (id, product_type_id, name, code, data_type, unit_code, is_required) VALUES (6, 5, 'С косточкой', 'has_pit', 'boolean', NULL, true);
INSERT INTO public.attribute_definition (id, product_type_id, name, code, data_type, unit_code, is_required) VALUES (7, 6, 'Вес', 'weight', 'number', 'kg', true);
INSERT INTO public.attribute_definition (id, product_type_id, name, code, data_type, unit_code, is_required) VALUES (8, 7, 'Вес', 'weight', 'number', 'kg', true);


--
-- Data for Name: audit_log; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.audit_log (id, model, record_id, action, old_data, new_data, actor, created_at) VALUES (1, 'User', 'None', 'insert', 'null', '{"id": null, "username": "admin", "password_hash": "$pbkdf2-sha256$29000$01or5TwHIITQeu9dyzknZA$CiadUFX/ursgVMF5.INC0YAIquP7JUjD8gU84OqVmN4", "is_active": true, "is_superuser": true}', NULL, '2026-01-21 10:29:53.966988');


--
-- Data for Name: composite_component; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (2, 5, 4, 0.100000, 'jar_fraction', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (3, 6, 1, 2.000000, 'glass', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (4, 6, 5, 1.000000, 'piece', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (5, 13, 7, 1.000000, 'bottle', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (6, 13, 8, 1.000000, 'bottle', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (7, 13, 9, 1.000000, 'bottle', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (8, 13, 10, 1.000000, 'bottle', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (9, 13, 11, 1.000000, 'bottle', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (1, 5, 3, 0.100000, 'kg', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (10, 5, 12, 0.020000, 'kg', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (11, 6, 7, 0.167000, 'bottle', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (12, 6, 8, 0.167000, 'bottle', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (13, 6, 9, 0.167000, 'bottle', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (14, 6, 10, 0.167000, 'bottle', false, NULL);
INSERT INTO public.composite_component (id, parent_product_id, component_product_id, quantity, unit_code, substitution_allowed, rounding) VALUES (15, 6, 11, 0.167000, 'bottle', false, NULL);


--
-- Data for Name: inventory_snapshot; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.inventory_snapshot (id, location_id, taken_at, data) VALUES (1, 1, '2026-01-21 10:46:12.013908', '{"note": "Initial snapshot", "items": []}');
INSERT INTO public.inventory_snapshot (id, location_id, taken_at, data) VALUES (2, 3, '2026-01-21 18:07:43.423804', '{"note": "Initial snapshot", "items": []}');


--
-- Data for Name: location; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.location (id, name, kind, is_active) VALUES (1, 'Main bar', 'bar', true);
INSERT INTO public.location (id, name, kind, is_active) VALUES (2, 'Warehouse', 'warehouse', true);
INSERT INTO public.location (id, name, kind, is_active) VALUES (3, 'Bar 2', 'bar', true);


--
-- Data for Name: permission; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.permission (id, code, description) VALUES (1, 'product.read', NULL);
INSERT INTO public.permission (id, code, description) VALUES (2, 'product.write', NULL);
INSERT INTO public.permission (id, code, description) VALUES (3, 'stock.write', NULL);
INSERT INTO public.permission (id, code, description) VALUES (4, 'user.read', NULL);
INSERT INTO public.permission (id, code, description) VALUES (5, 'user.write', NULL);


--
-- Data for Name: price_list; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (1, 1, 1, 'bottle', 'USD', 25.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (2, 1, 3, 'loaf_fraction', 'USD', 1.50);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (3, 1, 5, 'piece', 'USD', 6.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (4, 1, 6, 'piece', 'USD', 12.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (5, 2, 1, 'bottle', 'USD', 25.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (6, 2, 3, 'loaf_fraction', 'USD', 1.50);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (7, 2, 5, 'piece', 'USD', 6.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (8, 2, 6, 'piece', 'USD', 12.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (9, 3, 7, 'bottle', 'USD', 500.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (10, 3, 8, 'bottle', 'USD', 400.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (11, 3, 9, 'bottle', 'USD', 450.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (12, 3, 10, 'bottle', 'USD', 600.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (13, 3, 11, 'bottle', 'USD', 700.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (14, 3, 4, 'kg', 'USD', 200.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (15, 3, 3, 'kg', 'USD', 50.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (16, 3, 12, 'kg', 'USD', 80.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (17, 3, 13, 'piece', 'USD', 2000.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (18, 3, 5, 'piece', 'USD', 30.00);
INSERT INTO public.price_list (id, location_id, product_id, unit_code, currency, amount) VALUES (19, 3, 6, 'piece', 'USD', 500.00);


--
-- Data for Name: product; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (1, 'Merlot', 'WINE001', 'wine', 1, 'bottle', false, true, NULL, 0.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (2, 'Rioja Reserva', 'WINE002', 'wine', 1, 'bottle', false, true, NULL, 0.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (7, 'Красное сухое вино', 'WINE_R1', 'Вино', 4, 'bottle', false, true, NULL, 500.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (8, 'Белое полусладкое вино', 'WINE_W1', 'Вино', 4, 'bottle', false, true, NULL, 400.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (9, 'Розовое вино', 'WINE_P1', 'Вино', 4, 'bottle', false, true, NULL, 450.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (10, 'Игристое вино', 'WINE_S1', 'Вино', 4, 'bottle', false, true, NULL, 600.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (11, 'Десертное вино', 'WINE_D1', 'Вино', 4, 'bottle', false, true, NULL, 700.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (3, 'Багет', 'BREAD001', 'Хлеб', 6, 'kg', false, true, NULL, 50.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (4, 'Чёрные оливки', 'OLIVE001', 'Оливки', 5, 'kg', false, true, NULL, 200.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (12, 'Томатная паста', 'PASTE001', 'Томатная паста', 7, 'kg', false, true, NULL, 80.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (13, 'Корзина из 5 вин', 'SET_WINE', 'Корзина вин', 8, 'piece', true, true, NULL, 2000.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (5, 'Бутерброд', 'SNACK001', 'Бутерброд', 9, 'piece', true, true, NULL, 30.00);
INSERT INTO public.product (id, name, sku, primary_category, product_type_id, base_unit_code, is_composite, is_active, tax_flags, unit_cost) VALUES (6, 'Дегустационный набор', 'SET001', 'Дегустационный набор', 10, 'piece', true, true, NULL, 500.00);


--
-- Data for Name: product_attribute; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.product_attribute (id, product_id, name, value) VALUES (1, 1, 'vintage_year', '2018');
INSERT INTO public.product_attribute (id, product_id, name, value) VALUES (2, 1, 'glasses_per_bottle', '5');


--
-- Data for Name: product_attribute_value; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (7, 1, 0.750000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (7, 2, 12.500000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (7, 3, 6.000000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (8, 1, 0.750000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (8, 2, 11.000000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (8, 3, 6.000000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (9, 1, 0.750000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (9, 2, 13.000000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (9, 3, 6.000000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (10, 1, 0.750000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (10, 2, 12.000000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (10, 3, 6.000000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (11, 1, 0.500000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (11, 2, 15.000000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (11, 3, 4.000000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (4, 4, 0.500000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (4, 5, 150.000000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (4, 6, NULL, false, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (3, 7, 0.400000, NULL, NULL);
INSERT INTO public.product_attribute_value (product_id, attribute_definition_id, value_number, value_boolean, value_string) VALUES (12, 8, 0.200000, NULL, NULL);


--
-- Data for Name: product_category; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.product_category (id, product_id, category) VALUES (1, 1, 'red');


--
-- Data for Name: product_type; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.product_type (id, name, description, is_composite) VALUES (1, 'wine', 'Wine', false);
INSERT INTO public.product_type (id, name, description, is_composite) VALUES (2, 'bread', 'Bread', false);
INSERT INTO public.product_type (id, name, description, is_composite) VALUES (3, 'snack', 'Snacks', true);
INSERT INTO public.product_type (id, name, description, is_composite) VALUES (4, 'Вино', 'Wine', false);
INSERT INTO public.product_type (id, name, description, is_composite) VALUES (5, 'Оливки', 'Olives', false);
INSERT INTO public.product_type (id, name, description, is_composite) VALUES (6, 'Хлеб', 'Bread', false);
INSERT INTO public.product_type (id, name, description, is_composite) VALUES (7, 'Томатная паста', 'Tomato paste', false);
INSERT INTO public.product_type (id, name, description, is_composite) VALUES (8, 'Корзина вин', 'Wine basket', true);
INSERT INTO public.product_type (id, name, description, is_composite) VALUES (9, 'Бутерброд', 'Sandwich', true);
INSERT INTO public.product_type (id, name, description, is_composite) VALUES (10, 'Дегустационный набор', 'Tasting set', true);


--
-- Data for Name: request_log; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (1, '3404ea6d-d0c1-46dd-955f-9e98f35267b4', 'GET', '/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 10:50:38.30056');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (2, '4154de1b-74ec-43d5-a607-56ec3a6b531d', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 10:50:38.42534');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (3, '9a0142c4-2c09-48a6-a8c8-bb8cfdcdba9c', 'GET', '/docs', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 10:50:43.276677');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (4, 'c0070629-847b-44d9-abaf-42ab3f65bd4e', 'GET', '/openapi.json', 200, NULL, NULL, '{"duration_ms": 4}', '2026-01-21 10:50:44.526239');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (5, '533e17c4-1d00-4486-aacb-1dd476c36ce1', 'GET', '/api/v1/catalog', 200, NULL, NULL, '{"duration_ms": 8}', '2026-01-21 10:52:46.169074');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (6, 'ddefbddf-8080-4aad-90fc-71629bc8b80e', 'GET', '/api/v1/products', 401, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 11:08:31.042912');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (7, '73ffd1e3-85b0-4c37-863c-12b14656a17e', 'GET', '/api/v1/products', 401, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 11:08:48.940943');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (8, '5ca6ad48-954c-45b3-aba6-5dd43c866249', 'POST', '/api/v1/auth/token', 200, NULL, NULL, '{"duration_ms": 14}', '2026-01-21 11:09:20.567646');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (9, 'd796eb69-74d1-46a6-9c7b-2ac1dd39cc94', 'GET', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 4}', '2026-01-21 11:09:26.962887');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (10, '2ee4627b-5028-46bb-a656-55ce71e2ea76', 'OPTIONS', '/mock/dict/one', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 11:32:30.167483');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (11, '44c0a8d0-9ef2-42e4-b863-2e76cdd2d46b', 'OPTIONS', '/mock/dict/one', 200, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 11:32:30.176954');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (12, 'c0e296b1-51eb-43e0-9846-be6c60b567d1', 'OPTIONS', '/mock/dict/one', 200, NULL, NULL, '{"duration_ms": 4}', '2026-01-21 11:32:30.181549');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (13, '784ff3fa-0147-4800-b7cf-7cf2fb524e84', 'OPTIONS', '/mock/dict/one', 200, NULL, NULL, '{"duration_ms": 3}', '2026-01-21 11:32:30.184804');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (14, 'a42392f3-abc7-49e9-bf1f-5bc001a213d4', 'GET', '/mock/dict/one', 404, NULL, NULL, '{"duration_ms": 3}', '2026-01-21 11:32:30.187063');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (15, 'c1d46255-416f-4fb7-98a0-fabca31e1752', 'GET', '/mock/dict/one', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 11:32:30.189987');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (16, 'da4b5cc6-e5da-4496-a0fa-42bb048fa429', 'GET', '/mock/dict/one', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 11:32:30.19675');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (17, 'c3f2da5e-5f50-4c0d-a572-805da2fc166f', 'GET', '/mock/dict/one', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 11:32:30.200287');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (18, 'e7249dfe-71dc-4fe1-8c7e-33dfefd6db11', 'GET', '/mock/dict/one', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 11:32:31.674646');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (19, '98e67441-9df3-4ffb-ab3c-c07427a6f652', 'GET', '/mock/dict/one', 404, NULL, NULL, '{"duration_ms": 9}', '2026-01-21 11:32:31.683508');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (20, '850a0ccc-4af7-437b-8a26-dfbe80da4623', 'GET', '/mock/dict/one', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 11:32:31.686951');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (21, 'f8046979-9112-4aee-9619-c87e81bd9506', 'GET', '/mock/dict/one', 404, NULL, NULL, '{"duration_ms": 3}', '2026-01-21 11:32:31.689882');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (22, '870ddde4-e006-443f-b309-989b12cfeda4', 'GET', '/docs', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 13:36:53.823253');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (23, '19f007be-c233-4d0a-bc3e-abf338c5d7f0', 'GET', '/openapi.json', 200, NULL, NULL, '{"duration_ms": 14}', '2026-01-21 13:36:54.515669');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (24, '81fc630c-e085-45b3-8c31-9585a4389455', 'GET', '/api/v1/products', 401, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 13:37:38.485544');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (25, 'b568cd11-46a5-4f52-880b-a12d7ca5abd0', 'POST', '/api/v1/auth/token', 200, NULL, NULL, '{"duration_ms": 11}', '2026-01-21 13:37:51.42246');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (26, '4ed6c5f4-286d-4e8e-a4ad-9ea28346433d', 'GET', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 14}', '2026-01-21 13:37:53.720022');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (27, '4d45ef45-3687-4e9b-bdc1-4eae27785898', 'GET', '/docs', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 13:45:48.2814');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (28, 'b350f00f-5d35-435a-9428-e52ecc5d9b81', 'GET', '/openapi.json', 200, NULL, NULL, '{"duration_ms": 16}', '2026-01-21 13:45:48.728611');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (29, 'e2ffe77c-ce67-4ef4-bc74-48e476b5431d', 'GET', '/api/v1/products', 401, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 13:45:54.502079');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (30, '2afbbe77-384e-4eb4-b9b4-1c7795adc09c', 'POST', '/api/v1/auth/token', 200, NULL, NULL, '{"duration_ms": 14}', '2026-01-21 13:45:58.145978');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (31, '85956304-56bd-4273-a3b5-fe3ed660bb7d', 'POST', '/api/v1/auth/token', 200, NULL, NULL, '{"duration_ms": 7}', '2026-01-21 13:46:01.297347');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (32, '0ff19427-f1bc-4376-8714-001e697c30b5', 'GET', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 11}', '2026-01-21 13:46:03.933749');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (33, 'f6e7d3b4-b394-4898-aa04-9968a5620c71', 'GET', '/api/v1/products', 401, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 15:03:04.690055');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (34, '2d6ad1d9-332a-44aa-be63-c8709ef58d3c', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 15:03:04.830814');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (35, 'dd1d3a56-77d4-4467-a999-2f98270c038c', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 15:03:09.883574');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (36, 'e4bed13f-6ea8-41e1-bc46-924e16b2e8c2', 'GET', '/api/v1/products/', 307, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:29:50.636799');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (37, '3e162b51-303a-4597-bbfd-0febf71a5550', 'GET', '/api/v1/products', 401, NULL, NULL, '{"duration_ms": 3}', '2026-01-21 19:29:50.665254');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (38, '961591f1-fde7-42d4-b5a4-317bb8162a67', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:29:50.719843');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (69, '2db31698-6b63-493d-8c69-d272a2456107', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 19:34:57.550783');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (70, '467ff0fb-6b19-4ecc-bc15-c3febb101bc9', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 13}', '2026-01-21 19:34:57.563632');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (71, '6011fabb-9548-43f4-a07a-0e0450b5afb9', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:35:06.399639');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (72, '9d4910d1-8a91-4347-955e-8d65b10d00db', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 19:35:07.454149');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (73, 'eac9391b-fb74-48e1-82a1-db52dd4253c5', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:35:07.468966');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (74, '62474ff0-4f7d-4f89-8554-e028f5950d53', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:35:16.58408');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (75, 'be49c629-eea8-4b64-bfb6-6e8989de70bb', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:35:16.651855');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (76, 'def2552c-63a8-4b34-bc4c-578898222c9f', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:35:24.199196');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (77, '1fa5fb18-273b-4944-9e86-ed217f1909bc', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:36:55.181606');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (78, 'eb44b0ab-5f38-48f3-b1be-97dd56fa4b89', 'GET', '/v1/simple-catalog/products/ert', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:37:02.96323');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (79, '80430e66-4bea-43ec-8a38-7d1cd4da441f', 'GET', '/v1/simple-catalog/prod', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:37:07.02887');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (80, 'a230fd3b-4aaf-4a7e-a813-1d465544a008', 'GET', '/v1/simple-catalog/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:37:11.860716');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (81, 'b8d66250-7744-4d4c-8ffa-2780839d6a6b', 'GET', '/v1/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:37:16.337607');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (82, '8d720e6a-cf0f-4a7a-895b-08f37c71d8d2', 'GET', '/v1/products/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:37:35.315099');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (83, 'c15b0eab-c398-4ba1-9efd-181912bebb74', 'GET', '/v1/product-types/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:37:35.324274');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (84, '72cf9194-dbe3-4868-aa60-5e5e4f5bb12e', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:37:47.309511');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (85, '615ec4cf-3a04-47b0-8513-657703c8ea29', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 3}', '2026-01-21 19:37:47.317026');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (102, '7efb5f4f-4c3e-4b28-a91b-b1234db21b29', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 19:39:34.831206');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (103, 'f9fc0884-4a4b-4b73-8ab5-edd9e7cad3da', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 16}', '2026-01-21 19:39:34.845624');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (104, '063878ab-65e7-4338-b632-b58a18a8a2bc', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:39:44.664022');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (105, '1905c5a5-4f3a-4686-8300-839d61a3dec0', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 19:39:44.671095');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (106, 'e3edb519-cff1-415d-8c87-69f100f4aafa', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:41:48.075678');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (107, '6102d1b0-7506-4c12-bd5c-7fef83fedd8a', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 25}', '2026-01-21 19:41:55.613307');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (108, '7e286f88-868e-4167-9fc4-3db6d2a4d670', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:41:55.670429');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (109, 'c571d6a7-2a28-4435-888a-bd54ec9ada30', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:58:29.166998');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (110, 'd7db70ee-e3eb-47cd-bead-db9f6e9c8ce1', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 19:58:29.182126');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (111, 'bc91120a-2211-4064-986c-8445a7ac071d', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 19:58:36.837244');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (112, 'c3647d35-f84d-4a9e-b44d-4d3fe84929b5', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 19:58:36.851472');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (113, '9b256236-f9e5-449e-9861-d26008d21192', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 19:58:59.477234');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (114, 'ca09a1ea-8bb5-4213-a0cc-e357cb0f3987', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 19:58:59.492351');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (115, '2dd69b9c-a210-4bce-8558-1db083490c8b', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 20:04:41.734263');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (116, 'a3054cbb-adf4-4543-ab04-6e6334352dc6', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:04:41.743215');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (117, '535ee60b-b887-4506-8471-244e8d86d478', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:05:14.429882');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (148, '5deb615f-7c0b-4e6b-9f5d-73c8d5dc9074', 'GET', '/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:12:53.179775');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (149, 'd061d005-da23-4fb5-a730-db765d1069ef', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 19}', '2026-01-21 20:14:15.226036');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (150, '77e66d5d-3fca-4585-8f31-8c66dd702324', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 20:14:15.297436');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (151, '400dc266-2566-418c-8dcf-abc168ba899b', 'GET', '/йуц', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:14:32.983063');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (152, 'fd417274-8723-4f87-ba68-4c15beadf835', 'GET', '/v1/simple-catalog/products', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:14:39.830595');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (153, 'bd12b4cb-41f2-44a3-a1e7-a9afe21144a3', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:15:20.689635');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (154, '95189ef2-5437-4220-9842-6e0c0bbfb5f0', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:18:47.981038');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (155, '561602f0-f2d5-4479-83bc-672f97682be5', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:18:52.47763');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (156, 'cc161735-8cc5-4b7c-b0d5-3c763b6f1492', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 20:18:52.495374');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (157, '16cfc607-5d13-43f5-b41b-750a5419c7c2', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:18:56.057294');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (158, '084c8637-95ba-4fca-a0ba-fc3862561cdf', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:18:56.072821');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (159, 'baae24c3-4337-4955-b45a-87420744dc7b', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 20:24:53.001795');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (160, '3f3aded7-57be-47c6-b6ab-0edbc98e4e89', 'GET', '/api/v1/products', 401, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 20:24:55.159299');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (161, '43c2fd53-f71b-4ab8-8cfe-8d1746edb749', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:24:55.254563');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (162, 'bda7e795-3805-4c39-add7-379184f05e6d', 'GET', '/api/v1/products', 401, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:24:58.030419');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (163, 'acd8cab0-b231-4465-989a-0d9354d0e070', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:24:58.10956');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (164, '855b0dd0-4728-4d6c-9bf0-b4bc72c27eb4', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:32:48.392237');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (165, 'dd761589-7688-4d58-bd23-198e678dd3f6', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 20:32:48.405145');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (166, 'aae00dc3-b8ab-46a5-b138-803ddac7ac39', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 20:33:37.396504');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (167, 'bd9b6077-43c6-46b8-a715-fd42d61abe97', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 11}', '2026-01-21 20:33:39.306008');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (168, 'd525b5a2-d2e0-41c9-8442-96cc8f6628e9', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 20:33:39.395779');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (169, 'b179240f-c36f-404b-965a-5578f09bb1b5', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 38}', '2026-01-21 20:38:36.733494');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (170, 'f54ba629-a026-4c81-8cd8-07c08a081667', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 41}', '2026-01-21 20:44:39.0515');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (171, '288970f3-881e-4b15-922a-bd73798b635b', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 84}', '2026-01-21 20:44:39.09206');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (172, '6d2031a4-2723-4f91-aa92-cb6ffc3b71da', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 10}', '2026-01-21 20:44:53.943889');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (173, '65650bec-0c34-4f44-a438-a92c6e80051d', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 33}', '2026-01-21 20:44:53.992712');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (174, 'eed9a681-7e68-4c57-9026-8b8705666f2b', 'GET', '/api/v1/simple-catalog/products/5', 200, NULL, NULL, '{"duration_ms": 12}', '2026-01-21 20:44:54.020721');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (175, 'a46412d5-6a28-491b-aa45-11decc490c08', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 4}', '2026-01-21 20:45:02.954212');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (176, '9ba9a99d-3916-4985-a36f-770e4c8347ac', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 30}', '2026-01-21 20:45:03.048753');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (177, '012fe5b3-79ed-4ea9-be32-52ee97209ddb', 'GET', '/api/v1/simple-catalog/products/5', 200, NULL, NULL, '{"duration_ms": 6}', '2026-01-21 20:45:03.070656');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (178, 'f1d84ce0-7ef3-49f9-ac6e-e86ca796781f', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 19}', '2026-01-21 20:45:10.175198');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (179, 'b1fa059f-d825-4d67-abe1-baceeca79606', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 51}', '2026-01-21 20:45:10.20545');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (180, '4e900564-4aa4-4df3-ab19-fc93f8573321', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 11}', '2026-01-21 20:45:11.89456');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (181, '0afe217b-4cc3-4678-9411-16881e017206', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 49}', '2026-01-21 20:45:11.97632');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (182, 'b8e41d84-40df-4517-bf9c-f54ef876b979', 'GET', '/api/v1/simple-catalog/products/1', 200, NULL, NULL, '{"duration_ms": 3}', '2026-01-21 20:45:12.022476');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (183, '99f153b1-c201-4309-8d61-0ce5ced10631', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 8}', '2026-01-21 20:45:16.498643');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (184, 'b97ab976-9a0f-4015-b753-c0bba9f9b1e8', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 39}', '2026-01-21 20:45:16.526939');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (185, 'b8788292-05bb-4773-8425-4f77200dc877', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 19}', '2026-01-21 20:45:19.114792');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (186, 'f6c1f0ff-9aa0-4e3e-8e29-8dac36a35afd', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 66}', '2026-01-21 20:45:19.218507');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (187, '98d1eeb6-7999-40fa-ba43-b2e03182c5ac', 'GET', '/api/v1/simple-catalog/products/11', 200, NULL, NULL, '{"duration_ms": 6}', '2026-01-21 20:45:19.242871');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (188, '69c62abe-148a-4053-937f-cf78e23fa5af', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 8}', '2026-01-21 20:45:34.190489');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (189, 'cd80837f-f3af-417a-8f13-1db9cb491b61', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 34}', '2026-01-21 20:45:34.2133');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (190, '988c36f8-8341-454b-ac5b-562cf0adb1cb', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 9}', '2026-01-21 20:45:36.321577');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (191, '6fe56acd-a413-4b63-b3b8-72f372910f16', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 35}', '2026-01-21 20:45:36.385572');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (192, '9bc2c23f-4f05-4356-b0c1-cf4beed6249f', 'GET', '/api/v1/simple-catalog/products/1', 200, NULL, NULL, '{"duration_ms": 9}', '2026-01-21 20:45:36.44836');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (193, '08133d03-fd74-4ce5-a0d9-b49a30b1d010', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 19}', '2026-01-21 20:45:40.069969');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (194, '938d7c19-1eba-4f01-a851-c11df43931de', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 46}', '2026-01-21 20:45:40.094777');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (195, '44626c40-39dc-4432-9f6d-3f2a7322229d', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 9}', '2026-01-21 20:45:43.558384');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (196, '34c5889d-7c0e-4ab3-9b08-9cd9415265ed', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 33}', '2026-01-21 20:45:43.616111');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (197, 'beb91272-57f1-4659-a1a4-b9bdc71a5e4d', 'GET', '/api/v1/simple-catalog/products/7', 200, NULL, NULL, '{"duration_ms": 4}', '2026-01-21 20:45:43.67849');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (198, '88d5933d-c5c5-4310-a17b-8e2139d201b0', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 14}', '2026-01-21 20:57:40.907377');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (199, '8791be89-3076-4f9e-9b23-af48474b3ca1', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 42}', '2026-01-21 20:57:40.935316');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (200, 'a53d51ec-eeff-4875-b87d-1d381a3720e4', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 10}', '2026-01-21 20:58:24.710075');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (201, '27723555-b343-4100-8ed4-3874afe8e1bf', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 40}', '2026-01-21 20:58:24.780542');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (202, 'c0df18fe-456b-40bc-907b-cd757ac9c4f0', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 7}', '2026-01-21 20:58:28.463804');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (203, 'feb08c9a-ed10-4d89-bf56-0b4bd47160a8', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 30}', '2026-01-21 20:58:28.485482');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (204, '4c3b62f9-cb5f-4cb6-b28c-8bca5731c516', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 39}', '2026-01-21 21:38:41.544371');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (205, 'c955785f-9607-4cc3-ae09-2ce76463220b', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 73}', '2026-01-21 21:38:41.573569');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (206, 'ed42a2cc-54cb-4dd0-9fe7-8543885a1f74', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 6}', '2026-01-21 21:38:45.659792');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (207, 'c9daa140-2e52-4ee8-8386-de5744fa463e', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 30}', '2026-01-21 21:38:45.715075');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (208, '85cdb0b0-c8dc-40ab-b953-f018eb196b23', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 11}', '2026-01-21 21:38:50.247886');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (209, '4e36e7c3-de8a-4d0c-ab0c-817d72a350e0', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 37}', '2026-01-21 21:38:50.271627');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (210, 'e01de1df-a0f9-47a8-bb94-c6425fd6a581', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 28}', '2026-01-21 21:40:33.912498');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (211, '89ab6a2d-9816-48f5-93ff-cf1cf20ab745', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 73}', '2026-01-21 21:40:33.950807');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (212, '970f3e6d-7bcc-44a7-9e55-0f89df0eb4f0', 'OPTIONS', '/api/v1/auth/token', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 21:49:48.220239');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (213, 'ee5b85a5-f2dc-4b16-b152-d8b14d721ed1', 'POST', '/api/v1/auth/token', 200, NULL, NULL, '{"duration_ms": 10}', '2026-01-21 21:49:48.245385');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (214, '86096c8a-5f95-4bc5-b0d0-e93c0e194ee5', 'OPTIONS', '/mock/analysis/userAccessSource', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 21:49:53.50075');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (215, '89434785-9484-418e-bfad-f288e43c62df', 'OPTIONS', '/mock/analysis/weeklyUserActivity', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 21:49:53.555735');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (216, '157b1eda-8b35-442b-82f0-a8c0e612b207', 'OPTIONS', '/mock/analysis/monthlySales', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 21:49:53.559752');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (217, '5c1ee81a-67c7-4fa8-ad5d-f7a9a90cd08a', 'OPTIONS', '/mock/analysis/total', 200, NULL, NULL, '{"duration_ms": 4}', '2026-01-21 21:49:53.565128');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (218, 'a793c012-a5e4-4fdd-813d-608fa31c73aa', 'GET', '/mock/analysis/userAccessSource', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-21 21:49:53.636645');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (219, '4034128c-60c6-414d-9162-732bf87fadd1', 'GET', '/mock/analysis/weeklyUserActivity', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 21:49:53.64171');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (220, 'a53f056f-116c-4fac-9f7e-96559d318d0b', 'GET', '/mock/analysis/monthlySales', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 21:49:53.667235');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (221, '99b451b4-265c-4d2b-9a98-40bde54772b7', 'GET', '/mock/analysis/total', 404, NULL, NULL, '{"duration_ms": 2}', '2026-01-21 21:49:53.669765');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (222, '7d695f14-0ea7-4b63-b0fb-80edc4d81f8a', 'OPTIONS', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 21:50:01.428551');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (223, 'd1573869-e31d-4d7d-b62b-9f6ab221c769', 'GET', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 11}', '2026-01-21 21:50:01.473821');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (224, 'fc46ea3a-9eca-48ca-aaaa-552869510e48', 'OPTIONS', '/api/v1/catalog', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 21:50:09.272822');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (225, '9ba85b0f-cae2-48e9-8c67-b1c327e12e21', 'GET', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 25}', '2026-01-21 21:50:09.287597');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (226, '9a1c9035-a0a3-4c6e-a4cf-7b5eb406c121', 'GET', '/api/v1/catalog', 200, NULL, NULL, '{"duration_ms": 17}', '2026-01-21 21:50:09.39126');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (227, '3031403d-4e30-4360-9d74-f2de3e9b4cd6', 'GET', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 3}', '2026-01-21 21:50:29.799264');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (228, 'd42a9e4a-864f-4f33-9a23-781bad32d98e', 'GET', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 3}', '2026-01-21 21:50:40.557281');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (229, '5669bb7a-1ef6-45e3-b196-1218683236a1', 'GET', '/api/v1/products', 401, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 21:51:38.453994');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (230, '74c480ba-cc44-42ac-960e-35ad7ee632c1', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-21 21:51:38.621303');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (231, 'fba63872-7ab9-4f7a-a514-83dcf5e7b8ea', 'OPTIONS', '/api/v1/auth/token', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 09:51:17.081');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (232, '300e56e7-3887-4ea2-ac6f-8ad9784038f0', 'POST', '/api/v1/auth/token', 200, NULL, NULL, '{"duration_ms": 12}', '2026-01-22 09:51:17.103746');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (233, '78ff9ffc-c42e-4a8b-a17c-6e8733e4be7e', 'OPTIONS', '/mock/analysis/userAccessSource', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 09:51:20.234835');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (234, '59e9ad51-b231-4269-b42e-5cbc0fc7c896', 'OPTIONS', '/mock/analysis/weeklyUserActivity', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 09:51:20.24382');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (235, '0ad89c13-a25f-4c3c-8e6e-7dd8667d97f2', 'OPTIONS', '/mock/analysis/monthlySales', 200, NULL, NULL, '{"duration_ms": 5}', '2026-01-22 09:51:20.248074');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (236, '75c44d1b-d931-4ed7-9cc4-4978e854e58d', 'OPTIONS', '/mock/analysis/total', 200, NULL, NULL, '{"duration_ms": 6}', '2026-01-22 09:51:20.249437');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (237, 'ebf59b54-eb6d-4610-baee-dd06c52ef801', 'GET', '/mock/analysis/userAccessSource', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 09:51:20.261916');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (238, '1c0addd1-0197-4b05-9656-c547a53b02ff', 'GET', '/mock/analysis/weeklyUserActivity', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 09:51:20.301366');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (239, 'bdabe0de-0d47-4d1d-95cb-a70b142dcd24', 'GET', '/mock/analysis/monthlySales', 404, NULL, NULL, '{"duration_ms": 6}', '2026-01-22 09:51:20.308888');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (240, '3cb25e8c-f4b1-4132-ac40-d5a3216ca146', 'GET', '/mock/analysis/total', 404, NULL, NULL, '{"duration_ms": 10}', '2026-01-22 09:51:20.313225');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (241, 'a6aa6ac6-fe66-453b-808b-857e856c767f', 'GET', '/mock/analysis/userAccessSource', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-22 09:57:17.712932');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (242, '9cdaae6c-1273-4a27-b4f8-8c91444e46d7', 'GET', '/mock/analysis/total', 404, NULL, NULL, '{"duration_ms": 15}', '2026-01-22 09:57:17.72403');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (243, 'c910652c-f070-417a-ae6b-ff62a8dd2841', 'GET', '/mock/analysis/weeklyUserActivity', 404, NULL, NULL, '{"duration_ms": 17}', '2026-01-22 09:57:17.726259');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (244, '4acb8a73-934b-4a7b-98ac-53165e9a88de', 'GET', '/mock/analysis/monthlySales', 404, NULL, NULL, '{"duration_ms": 20}', '2026-01-22 09:57:17.728529');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (245, '4c9c587c-93bc-45d9-9b11-1a9df5ccd313', 'OPTIONS', '/mock/analysis/userAccessSource', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:03:33.066405');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (246, '5c16eef5-b8a8-475e-84de-a4c2b9a502f9', 'OPTIONS', '/mock/analysis/weeklyUserActivity', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:03:33.078113');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (247, '1f9f33c6-ffc3-4b0a-b4bc-02f8b5ea5bd2', 'OPTIONS', '/mock/analysis/monthlySales', 200, NULL, NULL, '{"duration_ms": 3}', '2026-01-22 10:03:33.081081');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (248, 'fe030cda-0bfa-4d50-b12d-400e3875e185', 'OPTIONS', '/mock/analysis/total', 200, NULL, NULL, '{"duration_ms": 6}', '2026-01-22 10:03:33.083343');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (249, '67aef887-cf87-439a-9562-5e2347a71d00', 'GET', '/mock/analysis/userAccessSource', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-22 10:03:33.236563');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (250, 'fed5ab11-f3ca-46e5-9cb4-2e060774e107', 'GET', '/mock/analysis/weeklyUserActivity', 404, NULL, NULL, '{"duration_ms": 14}', '2026-01-22 10:03:33.250798');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (251, '98931a33-d240-43e2-a97c-c8e525168111', 'GET', '/mock/analysis/monthlySales', 404, NULL, NULL, '{"duration_ms": 19}', '2026-01-22 10:03:33.257039');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (252, '6c14dd4c-b99f-4710-94a7-cac05387298e', 'GET', '/mock/analysis/total', 404, NULL, NULL, '{"duration_ms": 22}', '2026-01-22 10:03:33.258828');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (253, 'f2d443f0-5da5-4cec-acc6-b5100bb5509c', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:07:10.368735');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (254, '15949365-e78d-445c-a447-97ee97182aae', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 18}', '2026-01-22 10:07:12.643451');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (255, '7f6b9fee-7ae2-46ff-b7ca-611f703375a5', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:07:12.719015');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (256, 'c4646f3c-5ef4-47e2-a2bd-99c3233a90eb', 'OPTIONS', '/api/v1/catalog', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:12:57.056112');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (257, 'e8f4f6d3-40a8-45fc-8e02-9584f25f6ee1', 'OPTIONS', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:12:57.060765');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (258, 'dbce3e29-6655-4353-96e4-e2d5b42abd59', 'GET', '/api/v1/catalog', 200, NULL, NULL, '{"duration_ms": 33}', '2026-01-22 10:12:57.187088');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (259, '30fe5ea8-e70a-4ba4-a3cf-106e4473c031', 'GET', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 43}', '2026-01-22 10:12:57.199233');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (260, '6ad56652-de63-4d50-8b26-b32d584f0c16', 'GET', '/v1/simple-catalog/product-types/', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:15:08.97566');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (261, 'a171026a-086a-421f-b450-3a2b8871f9ad', 'GET', '/v1/simple-catalog/products/', 404, NULL, NULL, '{"duration_ms": 1}', '2026-01-22 10:15:09.236087');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (262, '38e56428-29f7-485d-b17a-dff14a5d78db', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 7}', '2026-01-22 10:22:04.172996');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (263, '9c1194ba-a0c5-43cd-b596-432014fb0740', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 50}', '2026-01-22 10:22:04.455219');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (264, 'f43ddab1-a844-4024-ac97-c36ce71150de', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 5}', '2026-01-22 10:22:18.66064');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (265, '5d02c8ad-8484-4d02-9876-6c90ca3a560c', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 54}', '2026-01-22 10:22:18.85726');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (266, '43990216-8a0a-4cb4-9511-ac412a1b2e88', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 15}', '2026-01-22 10:23:33.934554');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (267, '8092c635-c01a-4818-9115-e82a0577378a', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 95}', '2026-01-22 10:23:34.39293');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (268, '6526422e-09fe-4ea7-bc01-f02d13aa929a', 'OPTIONS', '/api/v1/catalog', 200, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:23:51.581557');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (269, 'd06f32ba-58e4-4c3d-8aab-69380f1953f6', 'OPTIONS', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 1}', '2026-01-22 10:23:51.59241');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (270, 'c9599c25-0a4c-47fa-9498-9c46982b3dd5', 'GET', '/api/v1/catalog', 200, NULL, NULL, '{"duration_ms": 11}', '2026-01-22 10:23:51.608217');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (271, '631eb3b9-c039-4306-8715-aff25d2ae65f', 'GET', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 19}', '2026-01-22 10:23:51.619878');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (272, '7a5f31d3-3031-446d-a5a9-7c15c10863cc', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 7}', '2026-01-22 10:24:23.898095');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (273, '582e0de0-e147-45a5-a4ea-29f97bc26d1c', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 51}', '2026-01-22 10:24:24.047441');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (274, 'd2fd83f1-f69a-46bd-9cb9-a76464ec7162', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 8}', '2026-01-22 10:24:36.810663');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (275, '50ceaebb-bca0-4af7-ac36-dd873bd24bc0', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 52}', '2026-01-22 10:24:37.05848');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (276, '17778456-7128-4dbb-849f-64298291c4f2', 'GET', '/api/v1/products', 200, NULL, NULL, '{"duration_ms": 4}', '2026-01-22 10:24:42.19363');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (277, 'bc5e74e5-720a-49ba-b720-a4a6805eab41', 'GET', '/api/v1/catalog', 200, NULL, NULL, '{"duration_ms": 13}', '2026-01-22 10:24:42.202653');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (278, 'eb8a2581-cf7f-4670-98a7-87b099d51998', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 4}', '2026-01-22 10:24:44.529681');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (279, 'c449e31f-420d-4f1f-ad86-71d86597684e', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 63}', '2026-01-22 10:24:44.708063');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (280, 'b8fdcd28-8010-4302-9746-fc7b167d93c2', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 25}', '2026-01-22 10:24:57.302717');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (281, '840a248b-0cbd-4fd5-ad76-e6e0d600ca26', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 9}', '2026-01-22 10:27:09.276324');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (282, '9fed3a5c-0de0-4757-9169-a9fd7156ad92', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 2}', '2026-01-22 10:27:09.374016');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (283, 'bcc48860-be0d-4bd6-882c-5dc133d8e1b5', 'GET', '/api/v1/simple-catalog/productы', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:27:15.265238');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (284, '2912628d-8c8c-49b2-8bab-f8105c2b3e97', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:27:15.380274');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (285, 'ef68c7d5-35c4-4b71-b632-a87f8ae6ca72', 'GET', '/api/v1/simple-catalog/products', 307, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:27:18.984438');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (286, '51b5d685-c099-4fc2-9170-2967a18af168', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 32}', '2026-01-22 10:27:19.053285');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (287, '13ac79f3-fb23-448a-bef9-3649ce2fff3e', 'GET', '/favicon.ico', 404, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 10:27:19.094515');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (288, 'c971b47d-4982-49b7-b736-fe2bc4df3ead', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 7}', '2026-01-22 10:37:12.605195');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (289, 'b8fd5f00-0ceb-44d3-a2fa-3abc161bc00f', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 79}', '2026-01-22 10:37:12.897965');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (290, '6b955a56-bab2-40ab-9887-2dbf76f9e845', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 9}', '2026-01-22 10:53:54.053041');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (291, '2f158967-b388-4297-93e5-7f13bacbd7c5', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 62}', '2026-01-22 10:53:54.345231');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (292, 'bbf9229f-a5c8-4ce8-bbc9-eab783117b2c', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 10}', '2026-01-22 10:55:07.49324');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (293, 'b53abe75-1bc7-4f26-a781-dcd42439554f', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 53}', '2026-01-22 10:55:07.727974');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (294, 'c844294b-84b4-4de9-b3d8-39785c427b31', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 29}', '2026-01-22 10:55:21.836516');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (295, 'a184f139-f9e5-4b06-bad1-98674a4e9578', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 11}', '2026-01-22 11:01:55.701358');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (296, '235748cc-924c-4143-8bdf-e007720dc162', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 61}', '2026-01-22 11:01:55.936738');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (297, 'bc3e6b10-1532-417c-bce3-ee369ca8ff89', 'GET', '/api/v1/simple-catalog/product-types/4', 200, NULL, NULL, '{"duration_ms": 2}', '2026-01-22 11:02:28.264781');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (298, '04a76c3b-7889-4d64-99ac-eacf1212a691', 'PUT', '/api/v1/simple-catalog/products/7', 422, NULL, NULL, '{"duration_ms": 0}', '2026-01-22 11:02:28.282217');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (299, '9f8065b1-61eb-4746-aa7d-baa87297c923', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 8}', '2026-01-22 11:11:39.290508');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (300, 'f16ee51c-36e7-453f-8632-0a7d5d01da58', 'GET', '/api/v1/simple-catalog/products/', 200, NULL, NULL, '{"duration_ms": 35}', '2026-01-22 11:11:39.979309');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (301, '94692248-c758-464a-a69f-ab3a9d62561e', 'GET', '/api/v1/simple-catalog/product-types/4', 200, NULL, NULL, '{"duration_ms": 2}', '2026-01-22 11:12:07.05253');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (302, '96152b89-37d8-4036-942b-9ec29b97b848', 'PUT', '/api/v1/simple-catalog/products/7', 422, NULL, NULL, '{"duration_ms": 1}', '2026-01-22 11:12:07.070157');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (303, 'bdb7f4d8-ff04-4173-a8a0-bcf6871bb61c', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 10}', '2026-01-22 11:35:01.514007');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (304, '4c4f6ace-a277-405f-bc61-340d98f3fbbc', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 9}', '2026-01-22 11:41:15.559181');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (305, 'd3c07c69-8424-4ca1-b826-fdd06a40a4ab', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 8}', '2026-01-22 11:45:25.315268');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (306, '865f0cd4-737f-41a6-b34a-db72b320b8e0', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 9}', '2026-01-22 11:45:37.61165');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (307, '83b28dac-ad4c-4389-aca7-35e77c82306d', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 13}', '2026-01-22 11:46:00.566221');
INSERT INTO public.request_log (id, request_id, method, path, status_code, user_id, terminal_id, context, created_at) VALUES (308, '389cf2a3-2b64-4538-8e0e-a120f7adc3ce', 'GET', '/api/v1/simple-catalog/product-types/', 200, NULL, NULL, '{"duration_ms": 6}', '2026-01-22 11:46:10.986378');


--
-- Data for Name: role; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.role (id, name, scope, location_id) VALUES (1, 'manager', 'global', NULL);


--
-- Data for Name: role_permission; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.role_permission (id, role_id, permission_id) VALUES (1, 1, 1);
INSERT INTO public.role_permission (id, role_id, permission_id) VALUES (2, 1, 2);
INSERT INTO public.role_permission (id, role_id, permission_id) VALUES (3, 1, 3);
INSERT INTO public.role_permission (id, role_id, permission_id) VALUES (4, 1, 4);
INSERT INTO public.role_permission (id, role_id, permission_id) VALUES (5, 1, 5);


--
-- Data for Name: sale_event; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.sale_event (id, event_id, terminal_id, location_id, payload, status, created_at, confirmed_at) VALUES (1, 'seed-sale-1', 1, 3, '{"lines": []}', 'pending', '2026-01-21 10:46:12.01583', NULL);


--
-- Data for Name: sale_line; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.sale_line (id, sale_event_id, product_id, quantity, unit_code, currency, price) VALUES (1, 1, 1, 1.000000, 'bottle', 'USD', 25.00);
INSERT INTO public.sale_line (id, sale_event_id, product_id, quantity, unit_code, currency, price) VALUES (2, 1, 7, 1.000000, 'bottle', 'USD', 25.00);


--
-- Data for Name: stock; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (1, 1, 1, 12.000000, 'bottle', '2026-01-21 10:46:11.970994');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (2, 1, 3, 5.000000, 'loaf_fraction', '2026-01-21 10:46:11.972037');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (3, 1, 4, 3.000000, 'jar_fraction', '2026-01-21 10:46:11.972806');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (4, 2, 1, 30.000000, 'bottle', '2026-01-21 10:46:11.973486');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (5, 3, 7, 10.000000, 'bottle', '2026-01-21 18:07:43.379507');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (6, 3, 8, 5.000000, 'bottle', '2026-01-21 18:07:43.382894');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (7, 3, 9, 8.000000, 'bottle', '2026-01-21 18:07:43.384356');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (8, 3, 10, 6.000000, 'bottle', '2026-01-21 18:07:43.385752');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (9, 3, 11, 4.000000, 'bottle', '2026-01-21 18:07:43.387007');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (10, 3, 4, 20.000000, 'kg', '2026-01-21 18:07:43.38819');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (11, 3, 3, 15.000000, 'kg', '2026-01-21 18:07:43.389502');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (12, 3, 12, 30.000000, 'kg', '2026-01-21 18:07:43.390698');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (13, 3, 13, 5.000000, 'piece', '2026-01-21 18:07:43.391731');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (14, 3, 5, 50.000000, 'piece', '2026-01-21 18:07:43.39279');
INSERT INTO public.stock (id, location_id, product_id, quantity, unit_code, updated_at) VALUES (15, 3, 6, 10.000000, 'piece', '2026-01-21 18:07:43.393891');


--
-- Data for Name: terminal; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.terminal (id, terminal_id, location_id, secret_hash, status) VALUES (2, 'T-2', 2, 'secret2', 'active');
INSERT INTO public.terminal (id, terminal_id, location_id, secret_hash, status) VALUES (1, 'T-1', 3, 'secret', 'active');


--
-- Data for Name: transfer; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.transfer (id, from_location_id, to_location_id, product_id, quantity, unit_code, created_at) VALUES (1, 2, 1, 1, 3.000000, 'bottle', '2026-01-21 10:46:12.012181');
INSERT INTO public.transfer (id, from_location_id, to_location_id, product_id, quantity, unit_code, created_at) VALUES (2, 3, 3, 7, 0.000000, 'bottle', '2026-01-21 18:07:43.421709');


--
-- Data for Name: unit; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.unit (code, description, ratio_to_base, discrete_step) VALUES ('gram', 'Gram', 1.000000, NULL);
INSERT INTO public.unit (code, description, ratio_to_base, discrete_step) VALUES ('loaf_fraction', 'Loaf fraction', 1.000000, 0.100000);
INSERT INTO public.unit (code, description, ratio_to_base, discrete_step) VALUES ('jar_fraction', 'Jar fraction', 1.000000, 0.100000);
INSERT INTO public.unit (code, description, ratio_to_base, discrete_step) VALUES ('liter', 'Литр', 1.000000, NULL);
INSERT INTO public.unit (code, description, ratio_to_base, discrete_step) VALUES ('kg', 'Килограмм', 1.000000, NULL);
INSERT INTO public.unit (code, description, ratio_to_base, discrete_step) VALUES ('bottle', 'Бутылка', 1.000000, NULL);
INSERT INTO public.unit (code, description, ratio_to_base, discrete_step) VALUES ('glass', 'Бокал', 0.166700, NULL);
INSERT INTO public.unit (code, description, ratio_to_base, discrete_step) VALUES ('piece', 'Штука', 1.000000, NULL);


--
-- Data for Name: unit_conversion; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.unit_conversion (id, from_unit, to_unit, ratio) VALUES (1, 'glass', 'bottle', 0.166700);


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public."user" (id, username, password_hash, is_active, is_superuser) VALUES (1, 'admin', '$pbkdf2-sha256$29000$rfXeW6sVolTK.b.3di5lDA$67gexear.bIp9cj14j07pRWesHNXNWzPVQuMI0Zc1Z4', true, true);
INSERT INTO public."user" (id, username, password_hash, is_active, is_superuser) VALUES (2, 'manager', '$pbkdf2-sha256$29000$a80ZY.z9n7P2vjfGOGeMEQ$5I8rWxJ9ynaBcAr9uvyOoR0JGKNtftx2zWeVmZRixHc', true, false);


--
-- Data for Name: user_role; Type: TABLE DATA; Schema: public; Owner: cavina
--

INSERT INTO public.user_role (id, user_id, role_id) VALUES (1, 2, 1);


--
-- Name: adjustment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.adjustment_id_seq', 2, true);


--
-- Name: attribute_definition_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.attribute_definition_id_seq', 8, true);


--
-- Name: auditlog_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.auditlog_id_seq', 1, true);


--
-- Name: compositecomponent_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.compositecomponent_id_seq', 15, true);


--
-- Name: inventorysnapshot_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.inventorysnapshot_id_seq', 2, true);


--
-- Name: location_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.location_id_seq', 3, true);


--
-- Name: permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.permission_id_seq', 5, true);


--
-- Name: pricelist_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.pricelist_id_seq', 19, true);


--
-- Name: product_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.product_id_seq', 13, true);


--
-- Name: productattribute_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.productattribute_id_seq', 2, true);


--
-- Name: productcategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.productcategory_id_seq', 1, true);


--
-- Name: producttype_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.producttype_id_seq', 10, true);


--
-- Name: requestlog_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.requestlog_id_seq', 308, true);


--
-- Name: role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.role_id_seq', 1, true);


--
-- Name: rolepermission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.rolepermission_id_seq', 5, true);


--
-- Name: saleevent_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.saleevent_id_seq', 1, true);


--
-- Name: saleline_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.saleline_id_seq', 2, true);


--
-- Name: stock_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.stock_id_seq', 15, true);


--
-- Name: terminal_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.terminal_id_seq', 2, true);


--
-- Name: transfer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.transfer_id_seq', 2, true);


--
-- Name: unitconversion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.unitconversion_id_seq', 1, true);


--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.user_id_seq', 2, true);


--
-- Name: userrole_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cavina
--

SELECT pg_catalog.setval('public.userrole_id_seq', 1, true);


--
-- Name: adjustment adjustment_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.adjustment
    ADD CONSTRAINT adjustment_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: attribute_definition attribute_definition_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.attribute_definition
    ADD CONSTRAINT attribute_definition_pkey PRIMARY KEY (id);


--
-- Name: audit_log auditlog_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT auditlog_pkey PRIMARY KEY (id);


--
-- Name: composite_component compositecomponent_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.composite_component
    ADD CONSTRAINT compositecomponent_pkey PRIMARY KEY (id);


--
-- Name: inventory_snapshot inventorysnapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.inventory_snapshot
    ADD CONSTRAINT inventorysnapshot_pkey PRIMARY KEY (id);


--
-- Name: location location_name_key; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.location
    ADD CONSTRAINT location_name_key UNIQUE (name);


--
-- Name: location location_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.location
    ADD CONSTRAINT location_pkey PRIMARY KEY (id);


--
-- Name: permission permission_code_key; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.permission
    ADD CONSTRAINT permission_code_key UNIQUE (code);


--
-- Name: permission permission_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.permission
    ADD CONSTRAINT permission_pkey PRIMARY KEY (id);


--
-- Name: price_list pricelist_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.price_list
    ADD CONSTRAINT pricelist_pkey PRIMARY KEY (id);


--
-- Name: product_attribute_value product_attribute_value_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_attribute_value
    ADD CONSTRAINT product_attribute_value_pkey PRIMARY KEY (product_id, attribute_definition_id);


--
-- Name: product product_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_pkey PRIMARY KEY (id);


--
-- Name: product product_sku_key; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_sku_key UNIQUE (sku);


--
-- Name: product_attribute productattribute_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_attribute
    ADD CONSTRAINT productattribute_pkey PRIMARY KEY (id);


--
-- Name: product_category productcategory_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_category
    ADD CONSTRAINT productcategory_pkey PRIMARY KEY (id);


--
-- Name: product_type producttype_name_key; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_type
    ADD CONSTRAINT producttype_name_key UNIQUE (name);


--
-- Name: product_type producttype_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_type
    ADD CONSTRAINT producttype_pkey PRIMARY KEY (id);


--
-- Name: request_log requestlog_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.request_log
    ADD CONSTRAINT requestlog_pkey PRIMARY KEY (id);


--
-- Name: role role_name_key; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_name_key UNIQUE (name);


--
-- Name: role role_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_pkey PRIMARY KEY (id);


--
-- Name: role_permission rolepermission_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.role_permission
    ADD CONSTRAINT rolepermission_pkey PRIMARY KEY (id);


--
-- Name: sale_event saleevent_event_id_key; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.sale_event
    ADD CONSTRAINT saleevent_event_id_key UNIQUE (event_id);


--
-- Name: sale_event saleevent_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.sale_event
    ADD CONSTRAINT saleevent_pkey PRIMARY KEY (id);


--
-- Name: sale_line saleline_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.sale_line
    ADD CONSTRAINT saleline_pkey PRIMARY KEY (id);


--
-- Name: stock stock_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.stock
    ADD CONSTRAINT stock_pkey PRIMARY KEY (id);


--
-- Name: terminal terminal_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.terminal
    ADD CONSTRAINT terminal_pkey PRIMARY KEY (id);


--
-- Name: terminal terminal_terminal_id_key; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.terminal
    ADD CONSTRAINT terminal_terminal_id_key UNIQUE (terminal_id);


--
-- Name: transfer transfer_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.transfer
    ADD CONSTRAINT transfer_pkey PRIMARY KEY (id);


--
-- Name: unit unit_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.unit
    ADD CONSTRAINT unit_pkey PRIMARY KEY (code);


--
-- Name: unit_conversion unitconversion_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.unit_conversion
    ADD CONSTRAINT unitconversion_pkey PRIMARY KEY (id);


--
-- Name: attribute_definition uq_attrdef_producttype_code; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.attribute_definition
    ADD CONSTRAINT uq_attrdef_producttype_code UNIQUE (product_type_id, code);


--
-- Name: composite_component uq_component_unique; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.composite_component
    ADD CONSTRAINT uq_component_unique UNIQUE (parent_product_id, component_product_id);


--
-- Name: price_list uq_price_location_product_unit; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.price_list
    ADD CONSTRAINT uq_price_location_product_unit UNIQUE (location_id, product_id, unit_code);


--
-- Name: product_attribute uq_product_attribute; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_attribute
    ADD CONSTRAINT uq_product_attribute UNIQUE (product_id, name);


--
-- Name: product_category uq_product_category; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_category
    ADD CONSTRAINT uq_product_category UNIQUE (product_id, category);


--
-- Name: role_permission uq_role_permission; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.role_permission
    ADD CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id);


--
-- Name: stock uq_stock_location_product; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.stock
    ADD CONSTRAINT uq_stock_location_product UNIQUE (location_id, product_id);


--
-- Name: unit_conversion uq_unit_conversion; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.unit_conversion
    ADD CONSTRAINT uq_unit_conversion UNIQUE (from_unit, to_unit);


--
-- Name: user_role uq_user_role; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT uq_user_role UNIQUE (user_id, role_id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: user user_username_key; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_username_key UNIQUE (username);


--
-- Name: user_role userrole_pkey; Type: CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT userrole_pkey PRIMARY KEY (id);


--
-- Name: adjustment adjustment_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.adjustment
    ADD CONSTRAINT adjustment_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(id);


--
-- Name: adjustment adjustment_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.adjustment
    ADD CONSTRAINT adjustment_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: adjustment adjustment_unit_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.adjustment
    ADD CONSTRAINT adjustment_unit_code_fkey FOREIGN KEY (unit_code) REFERENCES public.unit(code);


--
-- Name: attribute_definition attribute_definition_product_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.attribute_definition
    ADD CONSTRAINT attribute_definition_product_type_id_fkey FOREIGN KEY (product_type_id) REFERENCES public.product_type(id);


--
-- Name: attribute_definition attribute_definition_unit_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.attribute_definition
    ADD CONSTRAINT attribute_definition_unit_code_fkey FOREIGN KEY (unit_code) REFERENCES public.unit(code);


--
-- Name: composite_component compositecomponent_component_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.composite_component
    ADD CONSTRAINT compositecomponent_component_product_id_fkey FOREIGN KEY (component_product_id) REFERENCES public.product(id);


--
-- Name: composite_component compositecomponent_parent_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.composite_component
    ADD CONSTRAINT compositecomponent_parent_product_id_fkey FOREIGN KEY (parent_product_id) REFERENCES public.product(id);


--
-- Name: composite_component compositecomponent_unit_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.composite_component
    ADD CONSTRAINT compositecomponent_unit_code_fkey FOREIGN KEY (unit_code) REFERENCES public.unit(code);


--
-- Name: inventory_snapshot inventorysnapshot_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.inventory_snapshot
    ADD CONSTRAINT inventorysnapshot_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(id);


--
-- Name: price_list pricelist_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.price_list
    ADD CONSTRAINT pricelist_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(id);


--
-- Name: price_list pricelist_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.price_list
    ADD CONSTRAINT pricelist_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: price_list pricelist_unit_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.price_list
    ADD CONSTRAINT pricelist_unit_code_fkey FOREIGN KEY (unit_code) REFERENCES public.unit(code);


--
-- Name: product_attribute_value product_attribute_value_attribute_definition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_attribute_value
    ADD CONSTRAINT product_attribute_value_attribute_definition_id_fkey FOREIGN KEY (attribute_definition_id) REFERENCES public.attribute_definition(id);


--
-- Name: product_attribute_value product_attribute_value_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_attribute_value
    ADD CONSTRAINT product_attribute_value_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: product product_base_unit_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_base_unit_code_fkey FOREIGN KEY (base_unit_code) REFERENCES public.unit(code);


--
-- Name: product product_product_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_product_type_id_fkey FOREIGN KEY (product_type_id) REFERENCES public.product_type(id);


--
-- Name: product_attribute productattribute_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_attribute
    ADD CONSTRAINT productattribute_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: product_category productcategory_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.product_category
    ADD CONSTRAINT productcategory_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: request_log requestlog_terminal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.request_log
    ADD CONSTRAINT requestlog_terminal_id_fkey FOREIGN KEY (terminal_id) REFERENCES public.terminal(id);


--
-- Name: request_log requestlog_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.request_log
    ADD CONSTRAINT requestlog_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: role role_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(id);


--
-- Name: role_permission rolepermission_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.role_permission
    ADD CONSTRAINT rolepermission_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permission(id);


--
-- Name: role_permission rolepermission_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.role_permission
    ADD CONSTRAINT rolepermission_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.role(id);


--
-- Name: sale_event saleevent_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.sale_event
    ADD CONSTRAINT saleevent_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(id);


--
-- Name: sale_event saleevent_terminal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.sale_event
    ADD CONSTRAINT saleevent_terminal_id_fkey FOREIGN KEY (terminal_id) REFERENCES public.terminal(id);


--
-- Name: sale_line saleline_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.sale_line
    ADD CONSTRAINT saleline_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: sale_line saleline_sale_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.sale_line
    ADD CONSTRAINT saleline_sale_event_id_fkey FOREIGN KEY (sale_event_id) REFERENCES public.sale_event(id);


--
-- Name: sale_line saleline_unit_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.sale_line
    ADD CONSTRAINT saleline_unit_code_fkey FOREIGN KEY (unit_code) REFERENCES public.unit(code);


--
-- Name: stock stock_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.stock
    ADD CONSTRAINT stock_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(id);


--
-- Name: stock stock_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.stock
    ADD CONSTRAINT stock_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: stock stock_unit_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.stock
    ADD CONSTRAINT stock_unit_code_fkey FOREIGN KEY (unit_code) REFERENCES public.unit(code);


--
-- Name: terminal terminal_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.terminal
    ADD CONSTRAINT terminal_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(id);


--
-- Name: transfer transfer_from_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.transfer
    ADD CONSTRAINT transfer_from_location_id_fkey FOREIGN KEY (from_location_id) REFERENCES public.location(id);


--
-- Name: transfer transfer_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.transfer
    ADD CONSTRAINT transfer_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: transfer transfer_to_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.transfer
    ADD CONSTRAINT transfer_to_location_id_fkey FOREIGN KEY (to_location_id) REFERENCES public.location(id);


--
-- Name: transfer transfer_unit_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.transfer
    ADD CONSTRAINT transfer_unit_code_fkey FOREIGN KEY (unit_code) REFERENCES public.unit(code);


--
-- Name: unit_conversion unitconversion_from_unit_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.unit_conversion
    ADD CONSTRAINT unitconversion_from_unit_fkey FOREIGN KEY (from_unit) REFERENCES public.unit(code);


--
-- Name: unit_conversion unitconversion_to_unit_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.unit_conversion
    ADD CONSTRAINT unitconversion_to_unit_fkey FOREIGN KEY (to_unit) REFERENCES public.unit(code);


--
-- Name: user_role userrole_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT userrole_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.role(id);


--
-- Name: user_role userrole_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cavina
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT userrole_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- PostgreSQL database dump complete
--

\unrestrict clDmz6pNT1V4BIcZ2OK3QWEukyiuAC3CMrqZhSBHH3XiQhRazBShag5Fk8fo6wh

