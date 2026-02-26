import axios from 'axios'

// Helper function to convert snake_case to camelCase
function snakeToCamel(obj: any): any {
  if (obj === null || typeof obj !== 'object') {
    return obj
  }

  if (Array.isArray(obj)) {
    return obj.map(snakeToCamel)
  }

  const convertedObj: any = {}
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      const camelKey = key.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase())
      convertedObj[camelKey] = snakeToCamel(obj[key])
    }
  }
  return convertedObj
}

const api = axios.create({
  baseURL: '/api/v1/',
})

// Request interceptor to add JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to convert snake_case to camelCase
api.interceptors.response.use(
  (response) => {
    response.data = snakeToCamel(response.data)
    return response
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ==================== Types ====================

export interface Unit {
  id: number
  code: string
  description: string
  unitType: string // 'base', 'package', 'portion'
  isDiscrete: boolean
}

export interface ProductUnit {
  id: number
  unitId: number
  unitCode?: string
  unitDescription?: string
  unitType?: string
  ratioToBase: number
  discreteStep: number | null
  isBase?: boolean
}

export interface ProductComponent {
  id: number
  ingredientId: number
  ingredientName?: string | null
  quantity: number
  unitId: number
  unitCode?: string | null
  substitutionAllowed: boolean
  rounding?: string | null
  wasteFactor?: string | number
}

export interface ProductComponentTreeNode {
  ingredientId: number
  ingredientName: string
  quantity: number
  unitId: number
  unitCode?: string | null
  boundProductId?: number | null
  boundProductName?: string | null
  boundProductIsComposite: boolean
  availableQuantity: number
  isCycle: boolean
  children: ProductComponentTreeNode[]
}

export interface Ingredient {
  id: number
  code: string
  name: string
  baseUnitId: number
  description?: string | null
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface ProductAttributeValue {
  productAttributeId: number
  value: string
}

export interface ProductAttributeDefinition {
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
  attributes: ProductAttributeDefinition[]
  productTypeUnits?: ProductTypeUnit[]
}

export interface ProductTypeUnit {
  id?: number | null
  productTypeId?: number
  unitId: number
  ratioToBase: number
  discreteStep: number | null
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

export interface Product {
  id: number
  productTypeId: number
  name: string
  sku?: string | null
  stock: number
  baseCost: number
  isComposite: boolean
  baseUnitId: number
  attributes: ProductAttributeValue[]
  components: ProductComponent[]
  productUnits?: ProductUnit[]
}

export interface ProductView extends Product {
  meta?: ProductMetaView | null
  componentTree?: ProductComponentTreeNode[]
  stockByLocation?: ProductStockLocationView[]
}

export interface ProductUsageExample {
  type: 'base_unit_sale' | 'fractional_unit_sale' | 'component_usage'
  title: string
  description: string
  unitId?: number
  ratio?: string
  parentProductId?: number
  parentProductName?: string
  quantity?: string
  unitCode?: string | null
}

export interface ProductForm {
  productTypeId: number
  name: string
  sku?: string
  baseCost: string
  stock: string
  baseUnitId: number
  isComposite?: boolean
  attributes: Record<string, any>
  components: Array<{
    ingredientId: number
    quantity: number
    unitId?: number
    substitutionAllowed?: boolean
    rounding?: string | null
  }>
  productUnits: Array<{
    unitId: number
    ratioToBase: number
    discreteStep: number | null
  }>
}

export interface ProductUnitCreate {
  unitId: number
  ratioToBase: number
  discreteStep?: number | null
}

export interface ProductUnitUpdate {
  ratioToBase: number
  discreteStep?: number | null
}

export interface ProductComponentCreate {
  ingredientId: number
  quantity: number
  unitId?: number
  substitutionAllowed?: boolean
  rounding?: string | null
}

export interface ProductComponentUpdate {
  quantity?: number
  unitId?: number
  substitutionAllowed?: boolean
  rounding?: string | null
}

export interface ListProductsParams {
  locationId?: number
  productTypeId?: number
  name?: string
  skip?: number
  limit?: number
}

export interface FilterState {
  locationId: number | null
  productTypeId: number | null
  name: string
  isComposite: boolean | null
  unitId: number | null
}

export interface Location {
  id: number
  name: string
  code: string
}

// ==================== API Methods ====================

export const productApi2 = {
  /**
   * Get list of products with pagination and filters
   */
  async getProducts(params?: ListProductsParams): Promise<Product[]> {
    const queryParams = new URLSearchParams()
    if (params?.locationId) queryParams.append('location_id', params.locationId.toString())
    if (params?.productTypeId) queryParams.append('product_type_id', params.productTypeId.toString())
    if (params?.name && params.name.trim()) queryParams.append('name', params.name.trim())
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString())
    const effectiveLimit = params?.limit ?? 1000
    queryParams.append('limit', effectiveLimit.toString())

    const queryString = queryParams.toString()
    const url = queryString ? `products2?${queryString}` : 'products2'

    const res = await api.get<Product[]>(url)
    return res.data
  },

  /**
   * Get total count of products by filters
   */
  async getProductsCount(params?: Omit<ListProductsParams, 'skip' | 'limit'>): Promise<number> {
    const queryParams = new URLSearchParams()
    if (params?.locationId) queryParams.append('location_id', params.locationId.toString())
    if (params?.productTypeId) queryParams.append('product_type_id', params.productTypeId.toString())
    if (params?.name && params.name.trim()) queryParams.append('name', params.name.trim())

    const queryString = queryParams.toString()
    const url = queryString ? `products2/count?${queryString}` : 'products2/count'

    const res = await api.get<{ count: number }>(url)
    return res.data.count
  },

  /**
   * Get product by ID
   */
  async getProduct(id: number): Promise<Product> {
    const res = await api.get<Product>(`products2/${id}`)
    return res.data
  },

  /**
   * Get extended product view with component tree and stock
   */
  async getProductView(id: number): Promise<ProductView> {
    const res = await api.get<ProductView>(`products2/${id}/view`)
    return res.data
  },

  /**
   * Get component tree for composite product
   */
  async getComponentTree(id: number, locationId?: number): Promise<ProductComponentTreeNode[]> {
    const params = locationId ? { location_id: locationId } : {}
    const res = await api.get<ProductComponentTreeNode[]>(`products2/${id}/component-tree`, { params })
    return res.data
  },

  /**
   * Get fractional units for product
   */
  async getFractionalUnits(id: number): Promise<ProductUnit[]> {
    const res = await api.get<ProductUnit[]>(`products2/${id}/fractional-units`)
    return res.data
  },

  /**
   * Add fractional unit to product
   */
  async addFractionalUnit(productId: number, payload: ProductUnitCreate): Promise<ProductUnit> {
    const res = await api.post<ProductUnit>(`products2/${productId}/fractional-units`, payload)
    return res.data
  },

  /**
   * Update fractional unit ratio
   */
  async updateFractionalUnit(
    productId: number,
    unitId: number,
    payload: ProductUnitUpdate
  ): Promise<ProductUnit> {
    const res = await api.put<ProductUnit>(`products2/${productId}/fractional-units/${unitId}`, payload)
    return res.data
  },

  /**
   * Remove fractional unit from product
   */
  async removeFractionalUnit(productId: number, unitId: number): Promise<void> {
    await api.delete(`products2/${productId}/fractional-units/${unitId}`)
  },

  /**
   * Get components of composite product
   */
  async getComponents(id: number): Promise<ProductComponent[]> {
    const res = await api.get<ProductComponent[]>(`products2/${id}/components`)
    return res.data
  },

  /**
   * Add component to composite product
   */
  async addComponent(productId: number, payload: ProductComponentCreate): Promise<ProductComponent> {
    const res = await api.post<ProductComponent>(`products2/${productId}/components`, payload)
    return res.data
  },

  /**
   * Update component of composite product
   */
  async updateComponent(
    productId: number,
    componentId: number,
    payload: ProductComponentUpdate
  ): Promise<ProductComponent> {
    const res = await api.put<ProductComponent>(`products2/${productId}/components/${componentId}`, payload)
    return res.data
  },

  /**
   * Remove component from composite product
   */
  async removeComponent(productId: number, componentId: number): Promise<void> {
    await api.delete(`products2/${productId}/components/${componentId}`)
  },

  /**
   * Get usage examples for product
   */
  async getUsageExamples(id: number): Promise<ProductUsageExample[]> {
    const res = await api.get<ProductUsageExample[]>(`products2/${id}/usage-examples`)
    return res.data
  },

  /**
   * Create product
   */
  async createProduct(data: ProductForm): Promise<Product> {
    const productType = await api.get(`/../simple-catalog/product-types/${data.productTypeId}`)
    const attributeDefs = productType.data.attributes

    const attributes = Object.entries(data.attributes)
      .map(([code, value]) => {
        if (value === null || value === undefined || value === '') return null

        const attrDef = attributeDefs.find((def: ProductAttributeDefinition) => def.code === code)
        if (!attrDef) {
          console.warn(`Attribute definition not found for code: ${code}`)
          return null
        }

        return {
          product_attribute_id: attrDef.id,
          value: String(value)
        }
      })
      .filter(Boolean) as Array<{ product_attribute_id: number; value: string }>

    const components = (data.components || [])
      .filter(c => c.ingredientId > 0 && c.quantity > 0)
      .map(c => ({
        ingredient_id: c.ingredientId,
        quantity: c.quantity,
        unit_id: c.unitId,
        substitution_allowed: c.substitutionAllowed,
        rounding: c.rounding
      }))

    const payload = {
      product_type_id: data.productTypeId,
      name: data.name,
      sku: data.sku,
      base_cost: data.baseCost,
      stock: data.stock,
      base_unit_id: data.baseUnitId,
      is_composite: data.isComposite,
      attributes: attributes as Array<{ product_attribute_id: number; value: string }>,
      components,
      product_units: data.productUnits.map(pu => ({
        unit_id: pu.unitId,
        ratio_to_base: pu.ratioToBase,
        discrete_step: pu.discreteStep
      }))
    }

    const res = await api.post<Product>('products2', payload)
    return res.data
  },

  /**
   * Update product
   */
  async updateProduct(id: number, data: ProductForm): Promise<Product> {
    if (!data.productTypeId || typeof data.productTypeId !== 'number' || data.productTypeId <= 0) {
      throw new Error('Invalid productTypeId')
    }

    const productType = await api.get(`/../simple-catalog/product-types/${data.productTypeId}`)
    const attributeDefs = productType.data.attributes

    const attributes = Object.entries(data.attributes)
      .map(([code, value]) => {
        if (value === null || value === undefined || value === '') return null

        const attrDef = attributeDefs.find((def: ProductAttributeDefinition) => def.code === code)
        if (!attrDef) {
          console.warn(`Attribute definition not found for code: ${code}`)
          return null
        }

        return {
          product_attribute_id: attrDef.id,
          value: String(value)
        }
      })
      .filter(Boolean) as Array<{ product_attribute_id: number; value: string }>

    const components = (data.components || [])
      .filter(c => c.ingredientId > 0 && c.quantity > 0)
      .map(c => ({
        ingredient_id: c.ingredientId,
        quantity: c.quantity,
        unit_id: c.unitId,
        substitution_allowed: c.substitutionAllowed,
        rounding: c.rounding
      }))

    const payload = {
      product_type_id: data.productTypeId,
      name: data.name,
      sku: data.sku,
      base_cost: data.baseCost,
      stock: data.stock,
      base_unit_id: data.baseUnitId,
      is_composite: data.isComposite,
      attributes: attributes as Array<{ product_attribute_id: number; value: string }>,
      components,
      product_units: data.productUnits.map(pu => ({
        unit_id: pu.unitId,
        ratio_to_base: pu.ratioToBase,
        discrete_step: pu.discreteStep
      }))
    }

    const res = await api.put<Product>(`products2/${id}`, payload)
    return res.data
  },

  /**
   * Delete product
   */
  async deleteProduct(id: number): Promise<void> {
    await api.delete(`products2/${id}`)
  },

  /**
   * Upload product image
   */
  async uploadProductImage(id: number, file: File): Promise<{ image: string; imageUrl: string }> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await api.post<{ image: string; imageUrl: string }>(`products2/${id}/image`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return res.data
  },

  /**
   * Get all product types
   */
  async getProductTypes(): Promise<ProductType[]> {
    const res = await api.get<ProductType[]>('simple-catalog/product-types/')
    return res.data
  },

  /**
   * Get all units
   */
  async getUnits(): Promise<Unit[]> {
    const res = await api.get<Unit[]>('simple-catalog/units/')
    return res.data
  },

  /**
   * Get all locations
   */
  async getLocations(): Promise<Array<{ id: number; name: string; code: string }>> {
    const res = await api.get<Array<{ id: number; name: string; code: string }>>('simple-catalog/locations/')
    return res.data
  },

  async getIngredients(name?: string): Promise<Ingredient[]> {
    const params = name && name.trim() ? { name: name.trim() } : undefined
    const res = await api.get<Ingredient[]>('simple-catalog/ingredients', { params })
    return res.data
  },

  /**
   * Get all products for component selection (excluding composite cycles)
   */
  async getProductsForComponentSelection(excludeProductId?: number): Promise<Product[]> {
    const products = await this.getProducts({ limit: 1000 })
    if (excludeProductId) {
      return products.filter(p => p.id !== excludeProductId)
    }
    return products
  }
}
