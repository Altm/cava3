import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
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
  unitCost: number
  stock: number
  attributes: Record<string, any>
  components: Array<{ componentProductId: number; quantity: number }>
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

export const productApi = {
  async getProductTypes(): Promise<ProductType[]> {
    const res = await api.get<ProductType[]>('/product-types/')
    return res.data
  },

  async getProducts(): Promise<Product[]> {
    const res = await api.get<Product[]>('/products/')
    return res.data
  },

  async createProduct(data: ProductForm) {
    // First, we need to get the attribute definitions to map the values correctly
    const productType = await api.get(`/product-types/${data.productTypeId}`)
    const attributeDefs = productType.data.attributes
    
    // Convert attributes to the expected format
    const attributes = Object.entries(data.attributes).map(([code, value]) => {
      const attrDef = attributeDefs.find((def: AttributeDefinition) => def.code === code)
      if (!attrDef) {
        throw new Error(`Attribute definition not found for code: ${code}`)
      }
      return {
        attribute_definition_id: attrDef.id,
        value
      }
    })

    const payload = {
      product_type_id: data.productTypeId,
      name: data.name,
      unit_cost: data.unitCost,
      stock: data.stock,
      attributes,
      components: data.components.map(c => ({ [c.componentProductId]: c.quantity }))
    }

    return api.post('/products/', payload)
  },

  async updateProduct(id: number, data: ProductForm) {
    // First, we need to get the attribute definitions to map the values correctly
    const productType = await api.get(`/product-types/${data.productTypeId}`)
    const attributeDefs = productType.data.attributes
    
    // Convert attributes to the expected format
    const attributes = Object.entries(data.attributes).map(([code, value]) => {
      const attrDef = attributeDefs.find((def: AttributeDefinition) => def.code === code)
      if (!attrDef) {
        throw new Error(`Attribute definition not found for code: ${code}`)
      }
      return {
        attribute_definition_id: attrDef.id,
        value
      }
    })

    const payload = {
      product_type_id: data.productTypeId,
      name: data.name,
      unit_cost: data.unitCost,
      stock: data.stock,
      attributes,
      components: data.components.map(c => ({ [c.componentProductId]: c.quantity }))
    }

    return api.put(`/products/${id}`, payload)
  },

  async deleteProduct(id: number) {
    return api.delete(`/products/${id}`)
  },

  async getProduct(id: number): Promise<Product> {
    const res = await api.get<Product>(`/products/${id}`)
    return res.data
  }
}