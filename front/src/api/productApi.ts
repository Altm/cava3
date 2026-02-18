import axios from 'axios'

// Helper function to convert snake_case to camelCase
function snakeToCamel(obj: any): any {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map(snakeToCamel);
  }

  const convertedObj: any = {};
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      // Convert snake_case to camelCase
      const camelKey = key.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase());
      convertedObj[camelKey] = snakeToCamel(obj[key]);
    }
  }
  return convertedObj;
}

const api = axios.create({
  baseURL: '/api/v1/simple-catalog'
});

// Request interceptor to add JWT token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to convert snake_case to camelCase
api.interceptors.response.use(
  (response) => {
    response.data = snakeToCamel(response.data);
    return response;
  },
  (error) => {
    // Handle unauthorized access
    if (error.response && error.response.status === 401) {
      // Redirect to login page
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface AttributeDefinition {
  id: number
  name: string
  code: string
  dataType: 'number' | 'boolean' | 'string'
  unitId?: number
  isRequired: boolean
  sortOrder: number
}

export interface ProductType {
  id: number
  name: string
  description?: string | null
  isComposite: boolean
  strictUnitsByType?: boolean
  attributes: AttributeDefinition[]
  productTypeUnits?: ProductTypeUnit[]
}

export interface ProductForm {
  productTypeId: number
  name: string
  baseCost: string              // ← строка, не number!
  stock: string                 // ← строка
  baseUnitId: number            // ← добавляем baseUnitId
  isComposite?: boolean
  attributes: Record<string, any>
  components: Array<{
    componentProductId: number
    quantity: number
  }>
  productUnits: Array<{          // Add product-specific units
    unit_id: number
    ratio_to_base: number
    discrete_step: number | null
  }>
}

export interface ProductAttributeValue {
  productAttributeId: number;
  value: string;
}

export interface ProductComponent {
  id: number
  parentProductId: number
  componentProductId: number
  quantity: number
  unitId: number
  substitutionAllowed: boolean
  rounding?: string | null
}

export interface SaleRequest {
  productId: number
  quantity: number
}

export interface SaleResponse {
  message: string
  totalCost: number | string
}

export type SaleCheckoutLineKind = 'product' | 'item_qr' | 'box_qr' | 'glass'

export interface SaleCheckoutLineIn {
  kind: SaleCheckoutLineKind
  productId?: number
  quantity?: number | string
  unitId?: number
  qrCode?: string
  itemQrCode?: string
}

export interface SaleCheckoutRequest {
  lines: SaleCheckoutLineIn[]
}

export interface SaleCheckoutResolvedLine {
  kind: SaleCheckoutLineKind
  productId: number
  productName: string
  quantity: string
  unitId: number
  unitCode: string
  unitPrice: string
  totalPrice: string
  resolvedItemIds: number[]
  resolvedBoxId?: number | null
}

export interface SaleCheckoutOut {
  saleId: number
  terminalId: string
  locationId: number
  totalAmount: string
  lines: SaleCheckoutResolvedLine[]
  registerPayload: Record<string, any>
  registerResponse: Record<string, any>
}

export interface SalesListParams {
  status?: string
  locationId?: number
  terminalId?: string
  dateFrom?: string
  dateTo?: string
  limit?: number
}

export interface SaleListItem {
  id: number
  saleId?: number | null
  eventId: string
  status: string
  terminalId?: string | null
  locationId: number
  locationName?: string | null
  userId?: number | null
  linesCount: number
  totalAmount: string
  createdAt: string
  confirmedAt?: string | null
}

export interface SaleDetailLine {
  id: number
  productId: number
  productName: string
  productSku?: string | null
  quantity: string
  unitId: number
  unitCode: string
  currency: string
  lineTotalAmount: string
}

export interface SaleDetail {
  id: number
  saleId?: number | null
  eventId: string
  status: string
  terminalId?: string | null
  locationId: number
  locationName?: string | null
  userId?: number | null
  totalAmount: string
  createdAt: string
  confirmedAt?: string | null
  payload: Record<string, any>
  lines: SaleDetailLine[]
}

// Define the attribute structure as it comes from the API after snakeToCamel conversion
export interface ProductAttribute {
  productAttributeId: number;
  value: string;
}

export interface Unit {
  id: number;
  code: string;
  description: string;
  unitType: string;  // 'base', 'package', 'portion'
  isDiscrete: boolean;
}

export interface ProductUnit {
  id: number
  productId?: number
  unitId: number
  ratioToBase: number
  discreteStep: number | null
  source?: string | null
  product_id?: number
  unit_id?: number
  ratio_to_base?: number
  discrete_step?: number | null
}

export interface ProductTypeUnit {
  id?: number | null
  productTypeId?: number
  unitId: number
  ratioToBase: number
  discreteStep: number | null
  unit_id?: number
  ratio_to_base?: number
  discrete_step?: number | null
}

export interface Product {
  id: number
  productTypeId: number
  name: string
  stock: number
  baseCost: number
  isComposite: boolean
  baseUnitId: number;  // Add base unit ID
  attributes: ProductAttribute[];
  components: ProductComponent[]
  productUnits?: ProductUnit[];  // Add product-specific units
}

export interface ProductGlassLinkRequest {
  bottleUnitId: number
  glassUnitId: number
  glassesInBottle: number
  glassDiscreteStep?: string | number | null
}

export interface ProductGlassLinkOut {
  productId: number
  baseUnitId: number
  bottleUnitId: number
  bottleRatioToBase: string
  glassUnitId: number
  glassRatioToBase: string
  glassesInBottle: number
  productUnits: ProductUnit[]
}

export interface ProductMetaView {
  image?: string | null
  bodyHtml?: string | null
  vendor?: string | null
  type?: string | null
  tags?: string | null
  variantBarcode?: string | null
  seoTitle?: string | null
  seoDescription?: string | null
}

export interface ProductView extends Product {
  meta?: ProductMetaView | null
  componentTree?: ProductComponentTreeNode[]
  stockByLocation?: ProductStockLocationView[]
}

export interface ProductComponentTreeNode {
  componentProductId: number
  componentName: string
  quantity: number
  unitId: number
  unitCode?: string | null
  isComposite: boolean
  availableQuantity: number
  isCycle: boolean
  children: ProductComponentTreeNode[]
}

export interface ProductStockUnitQuantity {
  unitId: number
  unitCode: string
  ratioToBase: number
  quantity: number
}

export interface ProductStockLocationView {
  locationId: number
  locationName: string
  locationCode: string
  baseQuantity: number
  displayQuantity: string
  units: ProductStockUnitQuantity[]
}

export interface ProductImageOut {
  image: string
  imageUrl: string
}

export interface Location {
  id: number
  name: string
  code: string
}

export type PriceRevisionMode = 'percent' | 'fixed' | 'calculator'

export interface PriceCalculatorInfo {
  versionId: number
  calculatorCode: string
  calculatorName: string
  calculatorVersion: string
  sourceHash: string
  file: string
  className: string
  description?: string | null
}

export interface PriceRevisionCreateRequest {
  locationId: number
  name?: string
  mode: PriceRevisionMode
  currency?: string
  percentDelta?: string | number
  amountDelta?: string | number
  calculatorVersionId?: number
  calculatorFile?: string
  calculatorClass?: string
  calculatorParams?: Record<string, any>
}

export interface PriceRevisionItem {
  productId: number
  productName: string
  unitId: number
  unitCode: string
  currency: string
  amount: string
  previousAmount?: string | null
  basePrice?: string | null
  averagePurchaseCost?: string | null
  lots?: PriceItemLot[]
}

export interface PriceItemLot {
  lotId: number
  supplierLotNumber?: string | null
  receivedAt: string
  purchasePrice?: string | null
  inStockItems: number
}

export interface PriceRevisionListItem {
  id: number
  locationId: number
  locationName?: string | null
  name?: string | null
  mode: PriceRevisionMode
  currency: string
  percentDelta?: string | null
  amountDelta?: string | null
  calculatorVersionId?: number | null
  calculatorName?: string | null
  calculatorVersion?: string | null
  calculatorSourceHash?: string | null
  calculatorFile?: string | null
  calculatorClass?: string | null
  createdByUserId?: number | null
  createdAt: string
  effectiveFrom: string
  effectiveTo?: string | null
  itemsCount: number
}

export interface PriceRevisionDetail {
  id: number
  locationId: number
  locationName?: string | null
  name?: string | null
  mode: PriceRevisionMode
  currency: string
  percentDelta?: string | null
  amountDelta?: string | null
  calculatorVersionId?: number | null
  calculatorName?: string | null
  calculatorVersion?: string | null
  calculatorSourceHash?: string | null
  calculatorFile?: string | null
  calculatorClass?: string | null
  calculatorParams: Record<string, any>
  createdByUserId?: number | null
  createdAt: string
  items: PriceRevisionItem[]
}

export interface CurrentPriceOut {
  locationId: number
  locationName?: string | null
  revisionId?: number | null
  revisionName?: string | null
  revisionCalculatorName?: string | null
  revisionCalculatorVersion?: string | null
  revisionCalculatorSourceHash?: string | null
  revisionCreatedAt?: string | null
  items: PriceRevisionItem[]
}

export interface LotListItem {
  lotId: number
  productId: number
  productName: string
  supplierLotNumber?: string | null
  purchasePrice?: string | null
  receivedAt: string
  locationId: number
  locationName: string
  locationCode: string
  inStockItems: number
}

export interface LotItemDetail {
  productItemId: number
  productItemQrCode: string
  status: string
  locationId: number
  locationName: string
  locationCode?: string | null
  boxId?: number | null
  boxQrCode?: string | null
  createdAt: string
  updatedAt: string
}

export interface LotDetail {
  lotId: number
  productId: number
  productName: string
  supplierLotNumber?: string | null
  purchasePrice?: string | null
  receivedAt: string
  receiptId: number
  receiptStatus: string
  totalItems: number
  inStockItems: number
  items: LotItemDetail[]
}

export interface ProductWithStockByLocation {
  id: number
  productTypeId: number
  name: string
  stock: number
  baseCost: number
  isComposite: boolean
  attributes: Record<string, any>
  components: Array<{ componentProductId: number; quantity: number }>
  stockByLocation: Array<{ locationId: number; quantity: number }>
}

// Define the interface for creating/updating units
export interface CreateUnitRequest {
  code: string
  description: string
  unit_type: string  // 'base', 'package', 'portion'
  is_discrete: boolean
}

export interface UpdateUnitRequest {
  code: string
  description: string
  unit_type: string  // 'base', 'package', 'portion'
  is_discrete: boolean
}

export const productApi = {
  async getProductTypes(): Promise<ProductType[]> {
    const res = await api.get<ProductType[]>('/product-types/')
    return res.data
  },

  async getProducts(params?: { locationId?: number; productTypeId?: number; name?: string; skip?: number; limit?: number }): Promise<Product[]> {
    const queryParams = new URLSearchParams();
    if (params?.locationId) queryParams.append('location_id', params.locationId.toString());
    if (params?.productTypeId) queryParams.append('product_type_id', params.productTypeId.toString());
    if (params?.name && params.name.trim()) queryParams.append('name', params.name.trim());
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    const effectiveLimit = params?.limit ?? 1000;
    queryParams.append('limit', effectiveLimit.toString());

    const queryString = queryParams.toString();
    const url = queryString ? `/products/?${queryString}` : '/products/';

    const res = await api.get<Product[]>(url);
    return res.data;
  },

  async getProductsCount(params?: { locationId?: number; productTypeId?: number; name?: string }): Promise<number> {
    const queryParams = new URLSearchParams();
    if (params?.locationId) queryParams.append('location_id', params.locationId.toString());
    if (params?.productTypeId) queryParams.append('product_type_id', params.productTypeId.toString());
    if (params?.name && params.name.trim()) queryParams.append('name', params.name.trim());

    const queryString = queryParams.toString();
    const url = queryString ? `/products-count/?${queryString}` : '/products-count/';

    const res = await api.get<{ count: number }>(url);
    return res.data.count;
  },

  async createProduct(data: ProductForm) {
    // First, we need to get the attribute definitions to map the values correctly
    const productType = await api.get(`/product-types/${data.productTypeId}`)
    const attributeDefs = productType.data.attributes

    // Convert attributes to the expected format
    const attributes = Object.entries(data.attributes).map(([code, value]) => {
      // Only include attributes that have values (not null/undefined)
      if (value === null || value === undefined) {
        return null;
      }

      const attrDef = attributeDefs.find((def: AttributeDefinition) => def.code === code)
      if (!attrDef) {
        throw new Error(`Attribute definition not found for code: ${code}`)
      }
      return {
        product_attribute_id: attrDef.id,
        value
      }
    }).filter(Boolean); // Remove null entries

    const payload = {
      product_type_id: data.productTypeId,
      name: data.name,
      base_cost: data.baseCost,
      stock: data.stock,
      base_unit_id: data.baseUnitId,  // Add base unit ID
      is_composite: data.isComposite,  // Include the composite flag
      attributes: attributes as Array<{ product_attribute_id: number; value: string }>,
      components: data.components.map(c => ({
        component_product_id: c.componentProductId,
        quantity: c.quantity
      })),
      product_units: data.productUnits.map(pu => ({
        unit_id: pu.unit_id,
        ratio_to_base: pu.ratio_to_base,
        discrete_step: pu.discrete_step
      }))
    }

    return api.post('/products/', payload)
  },

  async updateProduct(id: number, data: ProductForm) {
  // 🔒 Validation: productTypeId must be a number > 0
  if (!data.productTypeId || typeof data.productTypeId !== 'number' || data.productTypeId <= 0) {
    throw new Error('Invalid productTypeId')
  }

  // Load product type for attribute mapping
  const productType = await api.get(`/product-types/${data.productTypeId}`)
  const attributeDefs = productType.data.attributes

  // Transform attributes
  const attributes = Object.entries(data.attributes)
    .map(([code, value]) => {
      if (value === null || value === undefined || value === '') return null

      const attrDef = attributeDefs.find((def: AttributeDefinition) => def.code === code)
      if (!attrDef) {
        console.warn(`Attribute definition not found for code: ${code}`)
        return null
      }

      return {
        product_attribute_id: attrDef.id,
        value: String(value) // always string!
      }
    })
    .filter(Boolean) as Array<{ product_attribute_id: number; value: string }>

  // ✅ Correct component format
  const components = (data.components || [])
    .filter(c => c.componentProductId > 0 && c.quantity > 0) // filter empty
    .map(c => ({
      component_product_id: c.componentProductId, // ← API keys
      quantity: c.quantity
    }))

  const payload = {
    product_type_id: data.productTypeId,
    name: data.name,
    base_cost: data.baseCost,   // string, e.g. "33.00"
    stock: data.stock,          // string, e.g. "44.000000"
    base_unit_id: data.baseUnitId,  // Add base unit ID
    is_composite: data.isComposite,  // Include the composite flag
    attributes: attributes as Array<{ product_attribute_id: number; value: string }>,
    components,
    product_units: data.productUnits.map(pu => ({
      unit_id: pu.unit_id,
      ratio_to_base: pu.ratio_to_base,
      discrete_step: pu.discrete_step
    }))
  }

  return api.put(`/products/${id}`, payload)
},

  async updateProductFractionLink(productId: number, payload: ProductGlassLinkRequest): Promise<ProductGlassLinkOut> {
    const requestPayload = {
      bottle_unit_id: payload.bottleUnitId,
      glass_unit_id: payload.glassUnitId,
      glasses_in_bottle: payload.glassesInBottle,
      glass_discrete_step: payload.glassDiscreteStep ?? 1,
    }
    const res = await api.put<ProductGlassLinkOut>(`/products/${productId}/fraction-link`, requestPayload)
    return res.data
  },

  async updateProductGlassLink(productId: number, payload: ProductGlassLinkRequest): Promise<ProductGlassLinkOut> {
    return this.updateProductFractionLink(productId, payload)
  },

  async sellProduct(saleRequest: SaleRequest): Promise<SaleResponse> {
    return api.post('/sales/', saleRequest).then(res => res.data);
  },

  async sellWineGlass(saleRequest: SaleRequest): Promise<SaleResponse> {
    return api.post('/glass-sales/', saleRequest).then(res => res.data);
  },

  async checkoutSales(payload: SaleCheckoutRequest): Promise<SaleCheckoutOut> {
    const requestPayload = {
      lines: (payload.lines || []).map((line) => ({
        kind: line.kind,
        product_id: line.productId,
        quantity: line.quantity,
        unit_id: line.unitId,
        qr_code: line.qrCode,
        item_qr_code: line.itemQrCode,
      })),
    }
    const res = await api.post<SaleCheckoutOut>('/sales/checkout', requestPayload)
    return res.data
  },

  async getSalesList(params?: SalesListParams): Promise<SaleListItem[]> {
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append('status', params.status)
    if (params?.locationId) queryParams.append('location_id', String(params.locationId))
    if (params?.terminalId) queryParams.append('terminal_id', params.terminalId)
    if (params?.dateFrom) queryParams.append('date_from', params.dateFrom)
    if (params?.dateTo) queryParams.append('date_to', params.dateTo)
    queryParams.append('limit', String(params?.limit ?? 100))
    const query = queryParams.toString()
    const url = query ? `/sales/list?${query}` : '/sales/list'
    const res = await api.get<SaleListItem[]>(url)
    return res.data
  },

  async getSale(id: number): Promise<SaleDetail> {
    const res = await api.get<SaleDetail>(`/sales/${id}`)
    return res.data
  },

  async confirmSale(id: number): Promise<SaleDetail> {
    const res = await api.post<SaleDetail>(`/sales/${id}/confirm`)
    return res.data
  },

  async deleteProduct(id: number) {
    return api.delete(`/products/${id}`)
  },

  async getProduct(id: number): Promise<Product> {
    const res = await api.get<Product>(`/products/${id}`)
    return res.data
  },

  async getProductView(id: number): Promise<ProductView> {
    const res = await api.get<ProductView>(`/products/${id}/view`)
    return res.data
  },

  async uploadProductImage(id: number, file: File): Promise<ProductImageOut> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await api.post<ProductImageOut>(`/products/${id}/image`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return res.data
  },

  async getLocations(): Promise<Location[]> {
    const res = await api.get<Location[]>('/locations/')
    return res.data
  },

  async createLocation(locationData: Omit<Location, 'id'>): Promise<Location> {
    const res = await api.post<Location>('/locations/', locationData)
    return res.data
  },

  async getPriceCalculators(): Promise<PriceCalculatorInfo[]> {
    const res = await api.get<PriceCalculatorInfo[]>('/prices/calculators')
    return res.data
  },

  async createPriceRevision(payload: PriceRevisionCreateRequest): Promise<PriceRevisionDetail> {
    const requestPayload = {
      location_id: payload.locationId,
      name: payload.name,
      mode: payload.mode,
      currency: payload.currency,
      percent_delta: payload.percentDelta,
      amount_delta: payload.amountDelta,
      calculator_version_id: payload.calculatorVersionId,
      calculator_file: payload.calculatorFile,
      calculator_class: payload.calculatorClass,
      calculator_params: payload.calculatorParams ?? {},
    }
    const res = await api.post<PriceRevisionDetail>('/prices/revisions', requestPayload)
    return res.data
  },

  async listPriceRevisions(params?: {
    locationId?: number
    dateFrom?: string
    dateTo?: string
    limit?: number
    offset?: number
  }): Promise<PriceRevisionListItem[]> {
    const queryParams = new URLSearchParams()
    if (params?.locationId) queryParams.append('location_id', String(params.locationId))
    if (params?.dateFrom) queryParams.append('date_from', params.dateFrom)
    if (params?.dateTo) queryParams.append('date_to', params.dateTo)
    if (params?.limit !== undefined) queryParams.append('limit', String(params.limit))
    if (params?.offset !== undefined) queryParams.append('offset', String(params.offset))
    const query = queryParams.toString()
    const url = query ? `/prices/revisions?${query}` : '/prices/revisions'
    const res = await api.get<PriceRevisionListItem[]>(url)
    return res.data
  },

  async getPriceRevision(revisionId: number): Promise<PriceRevisionDetail> {
    const res = await api.get<PriceRevisionDetail>(`/prices/revisions/${revisionId}`)
    return res.data
  },

  async getCurrentPrices(locationId: number): Promise<CurrentPriceOut> {
    const res = await api.get<CurrentPriceOut>('/prices/current', { params: { location_id: locationId } })
    return res.data
  },

  async listLots(params?: {
    locationId?: number
    productId?: number
    lotId?: number
    includeEmpty?: boolean
    limit?: number
    offset?: number
  }): Promise<LotListItem[]> {
    const queryParams = new URLSearchParams()
    if (params?.locationId) queryParams.append('location_id', String(params.locationId))
    if (params?.productId) queryParams.append('product_id', String(params.productId))
    if (params?.lotId) queryParams.append('lot_id', String(params.lotId))
    if (params?.includeEmpty) queryParams.append('include_empty', 'true')
    if (params?.limit !== undefined) queryParams.append('limit', String(params.limit))
    if (params?.offset !== undefined) queryParams.append('offset', String(params.offset))
    const query = queryParams.toString()
    const url = query ? `/lots?${query}` : '/lots'
    const res = await api.get<LotListItem[]>(url)
    return res.data
  },

  async getLot(lotId: number): Promise<LotDetail> {
    const res = await api.get<LotDetail>(`/lots/${lotId}`)
    return res.data
  },

  async createProductType(productTypeData: any): Promise<any> {
    const res = await api.post('/product-types/', productTypeData)
    return res.data
  },

  async updateProductType(id: number, productTypeData: any): Promise<any> {
    const res = await api.put(`/product-types/${id}`, productTypeData)
    return res.data
  },

  async deleteProductType(id: number): Promise<void> {
    await api.delete(`/product-types/${id}`)
  },

  async getUnits(): Promise<Unit[]> {
    const res = await api.get<Unit[]>('/units/')
    return res.data
  },

  async createUnit(unitData: CreateUnitRequest): Promise<Unit> {
    const res = await api.post<Unit>('/units/', unitData)
    return res.data
  },

  async updateUnit(id: number, unitData: UpdateUnitRequest): Promise<Unit> {
    const res = await api.put<Unit>(`/units/${id}`, unitData)
    return res.data
  },

  async deleteUnit(id: number): Promise<void> {
    await api.delete(`/units/${id}`)
  }
}
