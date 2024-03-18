import sys
from PyQt5 import QtWidgets, QtCore, QtGui
import os
import numpy as np
from PIL import Image
import xml.etree.ElementTree as ET

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.data_file_name = ''
        # self.scale_factor = 1.0
        self.initUI()
  
    def initUI(self):
        self.setWindowTitle('天问一号导航地形相机数据展示与转换v1.0')
        self.setGeometry(300, 300, 800, 600)

        # 创建布局和控件
        self.mainWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.mainWidget)
        self.layout = QtWidgets.QVBoxLayout(self.mainWidget)

        # 添加打开文件按钮
        self.fileButton = QtWidgets.QPushButton('打开文件（Open）')
        self.fileButton.clicked.connect(self.open_data_file)
        self.layout.addWidget(self.fileButton) 

        # 添加显示图像的标签
        # 创建滚动区域并将图像标签放入其中
        self.imageLabel = QtWidgets.QLabel(self)
        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.imageLabel)
        self.imageLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.scrollArea)
        
        # 添加显示解析信息的文本框
        # self.infoText = QtWidgets.QTextEdit()
        # self.infoText.setReadOnly(True)
        # self.layout.addWidget(self.infoText)

        # 添加另存为按钮
        self.saveButton = QtWidgets.QPushButton('另存为（Save as）')
        self.saveButton.clicked.connect(self.save_image)
        self.layout.addWidget(self.saveButton)

    # def wheelEvent(self, event):
    #     if event.angleDelta().y() > 0:
    #         self.scale_factor *= 1.1
    #     else:
    #         self.scale_factor /= 1.1

    #     self.imageLabel.resize(self.scale_factor * self.imageLabel.pixmap().size())

    def open_data_file(self):
        # 打开数据文件
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, '打开文件', '', 'PDS Files (*.2CL *.2BL *.xml)', options=options)
        if file_path:
            self.parse_and_display_file(file_path) 
            
    def parse_xml_and_get_image_data(self, xml_path):
        # 解析XML文件，并获取图像数据
        tree = ET.parse(xml_path)
        root = tree.getroot()
        NS = {"i":"http://pds.nasa.gov/pds4/pds/v1"}
        self.data_file_name = root.find('.//i:file_name', namespaces=NS).text
        array_3d_image = root.find('.//i:Array_3D_Image', namespaces=NS)
        if (self.data_file_name or array_3d_image) is None:
            return None, None
  
        element_array = array_3d_image.find('.//i:Element_Array', namespaces=NS)
        data_type = element_array.find('.//i:data_type', namespaces=NS).text
        unit = element_array.find('.//i:unit', namespaces=NS).text 
        # self.infoText.append('单位：'+unit) 
  
        axis_arrays = array_3d_image.findall('.//i:Axis_Array', namespaces=NS)
        dimensions = [int(a.find('.//i:elements', namespaces=NS).text) for a in axis_arrays]
  
        # 计算图像数据的总大小
        total_size = 1
        for dim in dimensions:
            total_size *= dim
            
        # self.infoText.append('大小：'+ str(total_size))
        
        # 读取二进制数据文件中的图像数据
        # data_file_path = array_3d_image.find('data_file_ref').text
        data_file_path = os.path.join(os.path.dirname(xml_path), self.data_file_name)
        with open(data_file_path, 'rb') as f:
            # 跳过offset指定的字节数
            f.seek(int(array_3d_image.find('.//i:offset', namespaces=NS).text))
            # 读取数据
            image_data = f.read(total_size)
  
        # 根据data_type将数据转换为合适的NumPy数据类型
        if data_type == 'UnsignedByte':
            image_data = np.frombuffer(image_data, dtype=np.uint8)
        # self.infoText.append('读取数据')
        
        # 重塑为三维数组
        image_data = image_data.reshape(dimensions)
        # self.infoText.append('重塑为三维数组') 
  
        return image_data, (dimensions, data_type, unit)
    
    def linear_percent_stretch(image_array, percent=2):
        # 计算亮度最高和最低2%像素的像素值
        brightest_pixel_value = np.percentile(image_array, 100 - percent)
        darkest_pixel_value = np.percentile(image_array, percent)
        
        # 线性拉伸剩余像素
        stretched_image = (image_array - darkest_pixel_value) * (255 / (brightest_pixel_value - darkest_pixel_value))
        
        # 将像素值剪裁到范围 [0, 255]
        stretched_image = np.clip(stretched_image, 0, 255)
        
        # 将像素值转换为 uint8 类型
        stretched_image = stretched_image.astype(np.uint8)
        
        return stretched_image
  
    def display_image(self, image_data, meta):
        # 显示图像
        if image_data is None:
            self.imageLabel.setText('无法加载图像数据')
            return
  
        # 如果图像是多波段的，我们可能需要选择某个波段来显示
        # 这里我们简单地选择第一个波段
        red_array = image_data[:, :, 0]
        green_array = image_data[:, :, 1]
        blue_array = image_data[:, :, 2]
  
        # 对每个通道应用线性百分比拉伸
        # red_stretched = self.linear_percent_stretch(red_array)
        # green_stretched = self.linear_percent_stretch(green_array)
        # blue_stretched = self.linear_percent_stretch(blue_array)
        
        # 合并三个数组为一个 RGB 图像
        rgb_image_array = np.stack((red_array, green_array, blue_array), axis=-1)
        # 将 numpy 数组转换为 PIL 图像
        image = Image.fromarray(rgb_image_array, mode='RGB')
        # image = Image.fromarray(band_to_display)
        image = image.convert('RGBA')
        width, height = image.size
        image_bytes = image.tobytes('raw', 'RGBA')
        # 将PIL图像对象显示在QLabel上
        pixmap = QtGui.QPixmap.fromImage(QtGui.QImage(image_bytes, width, height, QtGui.QImage.Format_RGBA8888))
        self.imageLabel.setPixmap(pixmap)
        self.imageLabel.setScaledContents(True)
  
        # 显示解析信息
        # info = f'Image shape: {image_data.shape}\nData type: {meta[1]}\nUnit: {meta[2]}'
        # self.infoText.append(info)
        
        self.image_data = image# 保存图像数据和元数据
        self.image_meta = meta
  
    def parse_and_display_file(self, file_path):
        # 解析并显示单个文件
        image_data, meta = self.parse_xml_and_get_image_data(file_path)
        self.display_image(image_data, meta)
              
    
    def save_image(self):
        if not hasattr(self, 'image_data') or not hasattr(self, 'image_meta'):
            # print('No image data to save.') 
            QtWidgets.QMessageBox.critical(self, '保存失败', f'无图像数据') 
            return

        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, '保存图像', '', 'JPEG Files (*.jpg);;All Files (*)')
        if filepath:
            try:
                image = self.image_data.convert('RGB')
                image.save(filepath, "JPEG")
                # print(f"Image saved successfully to {filepath}") 
                QtWidgets.QMessageBox.information(self, '保存成功', '图像保存成功！') 
            except Exception as e:
                # print(f"Error saving image: {e}")
                QtWidgets.QMessageBox.critical(self, '保存失败', f'图像保存失败：{e}')
                
def main():
    app = QtWidgets.QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
