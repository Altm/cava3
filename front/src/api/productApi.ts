import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1/simple-catalog'
})

export interface Unit {
  id: number
  symbol: string
  name: string
}

export interface AttributeDefinition {
  id: number
  name: string
  code: string
  dataType: 'number' | 'boolean' | 'string'
  unitId?: number
  isRequired: boolean
}

export interface ProductType {
  id: number
  name: string
  isComposite: boolean
  attributes: AttributeDefinition[]
}

export interface ProductForm {
  productTypeId: number
  name: string
  unitCost: string              // ← строка, не number!
  stock: string                 // ← строка
  attributes: Record<string, any>
  components: Array<{
    componentProductId: number
    quantity: number
  }>
}

export interface Product {
  id: number
  product_type_id: number
  name: string
  stock: number
  unit_cost: number
  is_composite: boolean
  attributes: Record<string, any>
  components: Array<{ componentProductId: number; quantity: number }>
}

export interface Location {
  id: number
  name: string
  kind: string
}

export interface ProductWithStockByLocation {
  id: number
  product_type_id: number
  name: string
  stock: number
  unit_cost: number
  is_composite: boolean
  attributes: Record<string, any>
  components: Array<{ componentProductId: number; quantity: number }>
  stock_by_location: Array<{ location_id: number; quantity: number }>
}

export const productApi = {
  async getProductTypes(): Promise<ProductType[]> {
    const res = await api.get<ProductType[]>('/product-types/')
    return res.data
  },

  async getProducts(params?: { locationId?: number; productTypeId?: number; skip?: number; limit?: number }): Promise<Product[]> {
    const queryParams = new URLSearchParams();
    if (params?.locationId) queryParams.append('location_id', params.locationId.toString());
    if (params?.productTypeId) queryParams.append('product_type_id', params.productTypeId.toString());
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());

    const queryString = queryParams.toString();
    const url = queryString ? `/products/?${queryString}` : '/products/';

    const res = await api.get<Product[]>(url);
    return res.data;
  },

  async getProductsCount(params?: { locationId?: number; productTypeId?: number }): Promise<number> {
    const queryParams = new URLSearchParams();
    if (params?.locationId) queryParams.append('location_id', params.locationId.toString());
    if (params?.productTypeId) queryParams.append('product_type_id', params.productTypeId.toString());

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
        attribute_definition_id: attrDef.id,
        value
      }
    }).filter(Boolean); // Remove null entries

    const payload = {
      product_type_id: data.productTypeId,
      name: data.name,
      unit_cost: data.unitCost,
      stock: data.stock,
      is_composite: data.isComposite,  // Include the composite flag
      attributes,
      components: data.components.map(c => ({
        component_product_id: c.componentProductId,
        quantity: c.quantity
      }))
    }

    return api.post('/products/', payload)
  },

async updateProduct(id: number, data: ProductForm) {
  // 🔒 Валидация: productTypeId должен быть числом > 0
  if (!data.productTypeId || typeof data.productTypeId !== 'number' || data.productTypeId <= 0) {
    throw new Error('Invalid productTypeId')
  }

  // Загружаем тип товара для маппинга атрибутов
  const productType = await api.get(`/product-types/${data.productTypeId}`)
  const attributeDefs = productType.data.attributes

  // Преобразуем атрибуты
  const attributes = Object.entries(data.attributes)
    .map(([code, value]) => {
      if (value === null || value === undefined || value === '') return null

      const attrDef = attributeDefs.find((def: AttributeDefinition) => def.code === code)
      if (!attrDef) {
        console.warn(`Attribute definition not found for code: ${code}`)
        return null
      }

      return {
        attribute_definition_id: attrDef.id,
        value: String(value) // всегда строка!
      }
    })
    .filter(Boolean) as Array<{ attribute_definition_id: number; value: string }>

  // ✅ Правильный формат компонентов
  const components = (data.components || [])
    .filter(c => c.componentProductId > 0 && c.quantity > 0) // фильтруем пустые
    .map(c => ({
      component_product_id: c.componentProductId, // ← ключи как в API
      quantity: c.quantity
    }))

  const payload = {
    product_type_id: data.productTypeId,
    name: data.name,
    unit_cost: data.unitCost,   // строка, например "33.00"
    stock: data.stock,          // строка, например "44.000000"
    is_composite: data.isComposite,  // Include the composite flag
    attributes,
    components
  }

  return api.put(`/products/${id}`, payload)
},

  async sellProduct(saleRequest: SaleRequest): Promise<SaleResponse> {
    return api.post('/sales/', saleRequest).then(res => res.data);
  },

  async sellWineGlass(saleRequest: SaleRequest): Promise<SaleResponse> {
    return api.post('/glass-sales/', saleRequest).then(res => res.data);
  },

  async deleteProduct(id: number) {
    return api.delete(`/products/${id}`)
  },

  async getProduct(id: number): Promise<Product> {
    const res = await api.get<Product>(`/products/${id}`)
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
  }
}
