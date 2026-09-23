import axios from 'axios'
const http = axios.create({ baseURL: '/api' })
export const promptsApi = {
  list: (params) => http.get('/prompts', { params }),
  create: (d) => http.post('/prompts', d),
  update: (id, d) => http.put(`/prompts/${id}`, d),
  remove: (id) => http.delete(`/prompts/${id}`),
}
export const libsApi = {
  groups: (lib) => http.get(`/libraries/${lib}/groups`),
  createGroup: (lib, name) => http.post(`/libraries/${lib}/groups`, { name }),
  renameGroup: (lib, id, name) => http.put(`/libraries/${lib}/groups/${id}`, { name }),
  deleteGroup: (lib, id) => http.delete(`/libraries/${lib}/groups/${id}`),
  images: (lib, params) => http.get(`/libraries/${lib}/images`, { params }),
  upload: (lib, groupId, files) => {
    const fd = new FormData()
    fd.append('group_id', groupId)
    files.forEach(f => fd.append('files', f))
    return http.post(`/libraries/${lib}/images`, fd)
  },
  updateImage: (lib, id, d) => http.put(`/libraries/${lib}/images/${id}`, d),
  deleteImage: (lib, id) => http.delete(`/libraries/${lib}/images/${id}`),
  importDir: (lib, source_dir) => http.post(`/libraries/${lib}/import-dir`, { source_dir }),
}
export const providersApi = {
  list: () => http.get('/providers'),
  create: (d) => http.post('/providers', d),
  update: (id, d) => http.put(`/providers/${id}`, d),
  remove: (id) => http.delete(`/providers/${id}`),
  test: (id) => http.post(`/providers/${id}/test`),
}
export const tasksApi = {
  create: (d) => http.post('/tasks', d),
  list: (params) => http.get('/tasks', { params }),
  detail: (id) => http.get(`/tasks/${id}`),
  rerun: (id) => http.post(`/tasks/${id}/rerun`),
  remove: (id) => http.delete(`/tasks/${id}`),
}
