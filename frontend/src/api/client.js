import axios from 'axios'

// Empty by default: requests go to a same-origin relative path (/api/v1/...),
// handled by the Vite dev-server proxy (see vite.config.js) or nginx in the
// Docker Compose stack. Set VITE_API_BASE_URL to a full origin only if the
// frontend and backend are deliberately served from different origins.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 60000,
})

export async function getHealth() {
  const { data } = await apiClient.get('/health')
  return data
}

export async function uploadTender({ file, title, referenceNo, category }) {
  const form = new FormData()
  form.append('file', file)
  form.append('title', title)
  if (referenceNo) form.append('reference_no', referenceNo)
  form.append('category', category || 'goods')
  const { data } = await apiClient.post('/tenders', form)
  return data
}

export async function uploadBid({ file, tenderId, vendorName, gstin, pan, udyamNumber, claimsMsmeBenefit }) {
  const form = new FormData()
  form.append('file', file)
  form.append('tender_id', tenderId)
  form.append('vendor_name', vendorName)
  if (gstin) form.append('gstin', gstin)
  if (pan) form.append('pan', pan)
  if (udyamNumber) form.append('udyam_number', udyamNumber)
  form.append('claims_msme_benefit', claimsMsmeBenefit ? 'true' : 'false')
  const { data } = await apiClient.post('/bids', form)
  return data
}

export async function getTenderPages(tenderId) {
  const { data } = await apiClient.get(`/tenders/${tenderId}/pages`)
  return data
}

export async function getTenderRequirements(tenderId) {
  const { data } = await apiClient.get(`/tenders/${tenderId}/requirements`)
  return data
}

export async function runVerification(bidId) {
  const { data } = await apiClient.post(`/bids/${bidId}/verification`)
  return data
}

export async function runCompliance(bidId) {
  const { data } = await apiClient.post(`/bids/${bidId}/compliance`)
  return data
}

export async function getCompliance(bidId) {
  const { data } = await apiClient.get(`/bids/${bidId}/compliance`)
  return data
}

export function getReportUrl(bidId) {
  return `${API_BASE_URL}/api/v1/bids/${bidId}/report`
}
