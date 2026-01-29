import { App } from 'vue';

// Импортируем только нужные компоненты для уменьшения размера бандла
import {
  ElButton,
  ElTable,
  ElTableColumn,
  ElCard,
  ElForm,
  ElFormItem,
  ElInput,
  ElSelect,
  ElOption,
  ElSwitch,
  ElTag,
  ElDialog,
  ElDivider,
  ElRow,
  ElCol,
  ElPagination,
  ElLoading,
  ElMessage,
  ElMessageBox
} from 'element-plus';

// Импортируем стили
import 'element-plus/theme-chalk/el-button.css';
import 'element-plus/theme-chalk/el-table.css';
import 'element-plus/theme-chalk/el-table-column.css';
import 'element-plus/theme-chalk/el-card.css';
import 'element-plus/theme-chalk/el-form.css';
import 'element-plus/theme-chalk/el-form-item.css';
import 'element-plus/theme-chalk/el-input.css';
import 'element-plus/theme-chalk/el-select.css';
import 'element-plus/theme-chalk/el-option.css';
import 'element-plus/theme-chalk/el-switch.css';
import 'element-plus/theme-chalk/el-tag.css';
import 'element-plus/theme-chalk/el-dialog.css';
import 'element-plus/theme-chalk/el-divider.css';
import 'element-plus/theme-chalk/el-row.css';
import 'element-plus/theme-chalk/el-col.css';
import 'element-plus/theme-chalk/el-pagination.css';
import 'element-plus/theme-chalk/base.css';

// Создаем плагин для регистрации компонентов
export default {
  install(app: App) {
    app.use(ElButton);
    app.use(ElTable);
    app.use(ElTableColumn);
    app.use(ElCard);
    app.use(ElForm);
    app.use(ElFormItem);
    app.use(ElInput);
    app.use(ElSelect);
    app.use(ElOption);
    app.use(ElSwitch);
    app.use(ElTag);
    app.use(ElDialog);
    app.use(ElDivider);
    app.use(ElRow);
    app.use(ElCol);
    app.use(ElPagination);
    app.use(ElLoading);
    
    // Глобальные директивы
    app.use(ElLoading.directive);
    
    // Глобальные методы
    app.config.globalProperties.$message = ElMessage;
    app.config.globalProperties.$msgbox = ElMessageBox;
    app.config.globalProperties.$alert = ElMessageBox.alert;
    app.config.globalProperties.$confirm = ElMessageBox.confirm;
    app.config.globalProperties.$prompt = ElMessageBox.prompt;
  }
};