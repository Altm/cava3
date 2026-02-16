import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1'
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export type ScanKind = 'ITM' | 'BOX'

export interface LabelsOut {
  labels: string[]
}

export interface ReceiptOut {
  id: number
  to_location_id: number
  status: string
}

export interface ReceiptListOut {
  id: number
  to_location_id: number
  status: string
  created_by_user_id?: number | null
  created_at: string
  updated_at: string
}

export interface ReceiptDetailOut extends ReceiptListOut {}

export interface ReceiptLineOut {
  id: number
  receipt_id: number
  product_id: number
  qty: string
  unit_id: number
  supplier_lot_number?: string | null
}

export interface ReceiptItemContentOut {
  product_item_id: number
  product_item_qr_code: string
  product_item_status: string
  product_item_created_at: string
  product_item_updated_at: string
  product_id: number
  product_name: string
  product_sku?: string | null
  purchase_amount: string
  lot_id: number
  supplier_lot_number?: string | null
  lot_received_at: string
  box_id?: number | null
  box_qr_code?: string | null
  location_id: number
  location_name: string
  location_code: string
  receipt_id: number
  receipt_status: string
  receipt_created_at: string
}

export interface ReceiptAutoBoxBoxOut {
  id: number
  qr_code: string
  product_id: number
  lot_id: number
  location_id: number
  sealed: boolean
  packed_items: number
}

export interface ReceiptAutoBoxOut {
  receipt_id: number
  items_per_box: number
  boxes_created: number
  items_packed: number
  items_remaining_unboxed: number
  boxes: ReceiptAutoBoxBoxOut[]
}

export interface BoxOut {
  id: number
  uuid: string
  qr_code: string
  product_id: number
  lot_id: number
  location_id: number
  sealed: boolean
  status: string
}

export interface BoxListOut {
  id: number
  uuid: string
  qr_code: string
  product_id: number
  lot_id: number
  location_id: number
  sealed: boolean
  status: string
  created_at: string
  updated_at: string
}

export interface TransferDocOut {
  id: number
  from_location_id: number
  to_location_id: number
  status: string
}

export interface TransferDocListOut {
  id: number
  from_location_id: number
  to_location_id: number
  status: string
  created_by_user_id?: number | null
  created_at: string
  updated_at: string
}

export interface TransferPlanLineOut {
  transfer_line_id: number
  product_id: number
  product_name: string
  qty_base: number
  pick_policy: string
  planned_qr_codes: string[]
}

export interface TransferDocDetailOut {
  id: number
  from_location_id: number
  to_location_id: number
  status: string
  created_by_user_id?: number | null
  created_at: string
  updated_at: string
  planned_count: number
  picked_count: number
  received_count: number
  removed_count: number
  transfer_lines: TransferPlanLineOut[]
}

export interface TransferPlanOut {
  transfer_doc_id: number
  transfer_line_id: number
  planned_items: number
}

export interface TransferItemMovementOut {
  transfer_item_id: number
  product_item_id: number
  product_item_qr_code: string
  product_id: number
  product_name: string
  transfer_item_state: string
  transfer_status: string
  transfer_created_at: string
  shipped_at?: string | null
  received_at?: string | null
  is_lost: boolean
}

export interface InventoryDocOut {
  id: number
  location_id: number
  status: string
}

export interface InventoryDocListOut {
  id: number
  location_id: number
  status: string
  created_by_user_id?: number | null
  closed_at?: string | null
  created_at: string
  updated_at: string
}

export interface InventoryDocDetailOut {
  id: number
  location_id: number
  status: string
  created_by_user_id?: number | null
  closed_at?: string | null
  created_at: string
  updated_at: string
  expected_count: number
  scanned_count: number
  missing_count: number
  unexpected_count: number
}

export interface ProductItemListOut {
  id: number
  uuid: string
  qr_code: string
  product_id: number
  lot_id: number
  location_id: number
  box_id?: number | null
  status: string
  reserved_transfer_doc_id?: number | null
  lost_reason?: string | null
  created_at: string
  updated_at: string
}

export interface ProductStockBalanceOut {
  location_id: number
  location_name: string
  quantity: string
}

export interface ProductItemTransferHistoryOut {
  transfer_doc_id: number
  from_location_id: number
  to_location_id: number
  transfer_status: string
  transfer_item_state: string
  transfer_created_at: string
  shipped_at?: string | null
  received_at?: string | null
  is_lost: boolean
}

export interface ProductItemHistorySummaryOut {
  product_item_id: number
  product_item_qr_code: string
  product_item_status: string
  product_item_location_id: number
  product_id: number
  product_name: string
  product_sku?: string | null
  lot_id: number
  current_base_cost: string
  item_purchase_amount: string
}

export interface ProductItemHistoryOut {
  summary: ProductItemHistorySummaryOut
  stock_balances: ProductStockBalanceOut[]
  transfers: ProductItemTransferHistoryOut[]
}

export interface ScanOut {
  kind: ScanKind
  found: boolean
  uuid: string

  id?: number | null
  status?: string | null
  location_id?: number | null

  // ITM
  product_id?: number | null
  lot_id?: number | null
  box_id?: number | null
  reserved_transfer_doc_id?: number | null

  // BOX
  sealed?: boolean | null
}

export const serialApi = {
  // Receipts
  async createReceipt(to_location_id: number): Promise<ReceiptOut> {
    const res = await api.post('/receipts', { to_location_id })
    return res.data
  },
  async addReceiptLine(receipt_id: number, product_id: number, qty: string, unit_id: number, supplier_lot_number?: string) {
    const res = await api.post(`/receipts/${receipt_id}/lines`, { product_id, qty, unit_id, supplier_lot_number })
    return res.data as ReceiptLineOut
  },
  async generateReceipt(receipt_id: number) {
    const res = await api.post(`/receipts/${receipt_id}/generate`)
    return res.data
  },
  async postReceipt(receipt_id: number) {
    const res = await api.post(`/receipts/${receipt_id}/post`)
    return res.data
  },
  async voidReceipt(receipt_id: number) {
    const res = await api.post(`/receipts/${receipt_id}/void`)
    return res.data
  },
  async receiptItemLabels(receipt_id: number): Promise<LabelsOut> {
    const res = await api.get(`/receipts/${receipt_id}/labels/items`)
    return res.data
  },
  async receiptAutoBox(
    receipt_id: number,
    payload: {
      items_per_box: number
      max_boxes?: number
      include_partial?: boolean
      seal_full_boxes?: boolean
      product_id?: number
      lot_id?: number
    }
  ): Promise<ReceiptAutoBoxOut> {
    const res = await api.post(`/receipts/${receipt_id}/auto-box`, payload)
    return res.data
  },
  async listReceipts(params?: {
    status?: string
    to_location_id?: number
    product_id?: number
    created_by_user_id?: number
    limit?: number
    offset?: number
  }): Promise<ReceiptListOut[]> {
    const res = await api.get('/receipts', { params })
    return res.data
  },
  async getReceipt(receipt_id: number): Promise<ReceiptDetailOut> {
    const res = await api.get(`/receipts/${receipt_id}`)
    return res.data
  },
  async listReceiptLines(receipt_id: number): Promise<ReceiptLineOut[]> {
    const res = await api.get(`/receipts/${receipt_id}/lines`)
    return res.data
  },
  async listReceiptItems(receipt_id: number): Promise<ReceiptItemContentOut[]> {
    const res = await api.get(`/receipts/${receipt_id}/items`)
    return res.data
  },
  async removeReceiptLine(receipt_id: number, line_id: number) {
    const res = await api.post(`/receipts/${receipt_id}/lines/${line_id}/remove`)
    return res.data
  },

  // Boxes
  async createBox(product_id: number, lot_id: number, location_id: number, sealed: boolean): Promise<BoxOut> {
    const res = await api.post('/boxes', { product_id, lot_id, location_id, sealed })
    return res.data
  },
  async getBox(box_id: number): Promise<BoxOut> {
    const res = await api.get(`/boxes/${box_id}`)
    return res.data
  },
  async openBox(box_id: number): Promise<BoxOut> {
    const res = await api.post(`/boxes/${box_id}/open`)
    return res.data
  },
  async sealBox(box_id: number): Promise<BoxOut> {
    const res = await api.post(`/boxes/${box_id}/seal`)
    return res.data
  },
  async addItemToBox(box_id: number, qr_code: string) {
    const res = await api.post(`/boxes/${box_id}/add-item`, { qr_code })
    return res.data
  },
  async boxLabels(box_id: number): Promise<LabelsOut> {
    const res = await api.get(`/boxes/${box_id}/labels`)
    return res.data
  },
  async listBoxes(params?: {
    status?: string
    sealed?: boolean
    location_id?: number
    product_id?: number
    lot_id?: number
    limit?: number
    offset?: number
  }): Promise<BoxListOut[]> {
    const res = await api.get('/boxes', { params })
    return res.data
  },

  // Transfers (serialized)
  async createTransfer(from_location_id: number, to_location_id: number): Promise<TransferDocOut> {
    const res = await api.post('/transfers', { from_location_id, to_location_id })
    return res.data
  },
  async planTransfer(transfer_doc_id: number, product_id: number, qty_base: number): Promise<TransferPlanOut> {
    const res = await api.post(`/transfers/${transfer_doc_id}/plan`, { product_id, qty_base })
    return res.data
  },
  async removeTransferItem(transfer_doc_id: number, product_item_id: number) {
    const res = await api.post(`/transfers/${transfer_doc_id}/remove-item`, { product_item_id })
    return res.data
  },
  async scanTransfer(transfer_doc_id: number, qr_code: string, mode: 'picking' | 'receiving') {
    const res = await api.post(`/transfers/${transfer_doc_id}/scan`, { qr_code, mode })
    return res.data
  },
  async shipTransfer(transfer_doc_id: number) {
    const res = await api.post(`/transfers/${transfer_doc_id}/ship`)
    return res.data
  },
  async closeTransfer(transfer_doc_id: number) {
    const res = await api.post(`/transfers/${transfer_doc_id}/close`)
    return res.data
  },
  async listTransfers(params?: {
    status?: string
    from_location_id?: number
    to_location_id?: number
    product_id?: number
    created_by_user_id?: number
    limit?: number
    offset?: number
  }): Promise<TransferDocListOut[]> {
    const res = await api.get('/transfers', { params })
    return res.data
  },
  async getTransfer(transfer_doc_id: number): Promise<TransferDocDetailOut> {
    const res = await api.get(`/transfers/${transfer_doc_id}`)
    return res.data
  },
  async listTransferItems(transfer_doc_id: number): Promise<TransferItemMovementOut[]> {
    const res = await api.get(`/transfers/${transfer_doc_id}/items`)
    return res.data
  },

  // Inventories (serialized)
  async createInventory(location_id: number): Promise<InventoryDocOut> {
    const res = await api.post('/inventories', { location_id })
    return res.data
  },
  async startInventory(inventory_doc_id: number) {
    const res = await api.post(`/inventories/${inventory_doc_id}/start`)
    return res.data
  },
  async scanInventory(inventory_doc_id: number, qr_code: string) {
    const res = await api.post(`/inventories/${inventory_doc_id}/scan`, { qr_code })
    return res.data
  },
  async closeInventory(inventory_doc_id: number) {
    const res = await api.post(`/inventories/${inventory_doc_id}/close`)
    return res.data
  },
  async listInventories(params?: {
    status?: string
    location_id?: number
    created_by_user_id?: number
    limit?: number
    offset?: number
  }): Promise<InventoryDocListOut[]> {
    const res = await api.get('/inventories', { params })
    return res.data
  },
  async getInventory(inventory_doc_id: number): Promise<InventoryDocDetailOut> {
    const res = await api.get(`/inventories/${inventory_doc_id}`)
    return res.data
  },

  // Product items
  async listProductItems(params?: {
    status?: string
    location_id?: number
    product_id?: number
    lot_id?: number
    box_id?: number
    reserved_transfer_doc_id?: number
    limit?: number
    offset?: number
  }): Promise<ProductItemListOut[]> {
    const res = await api.get('/scan/items', { params })
    return res.data
  },
  async getProductItemHistory(product_item_id: number): Promise<ProductItemHistoryOut> {
    const res = await api.get(`/scan/items/${product_item_id}/history`)
    return res.data
  },

  // Scan resolver
  async scanQr(qr_code: string): Promise<ScanOut> {
    const res = await api.post(`/scan/${encodeURIComponent(qr_code)}`)
    return res.data
  }
}
