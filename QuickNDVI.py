# -*- coding: utf-8 -*-

from osgeo import gdal, osr
import sys
import numpy as np

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm, 
QgsProcessingParameterRasterLayer,QgsProcessingParameterEnum,
QgsProcessingParameterRasterDestination, QgsMessageLog)



class RasterAlg(QgsProcessingAlgorithm):
    INPUT_RASTER = 'INPUT_RASTER'
    INPUT_MODE = 'INPUT_MODE'
    OUTPUT_RASTER = 'OUTPUT_RASTER'

    def __init__(self):
        super().__init__()

    def name(self):
        return "MIERUNE"

    def tr(self, text):
        return QCoreApplication.translate("MIERUNE", text)

#スクリプト名、グループ名、スクリプトの概要、ヘルプのリンク先
#the name of script, group, helpURL
    def displayName(self):
        return self.tr("QuickNDVI Script")

    def group(self):
        return self.tr("MIERUNE")

    def groupId(self):
        return "MIERUNE"

    def shortHelpString(self):
        return self.tr("QuickNDVI Script for satelite image")

    def helpUrl(self):
        return "https://www.mierune.co.jp"

    #Create the window for the parameters(input raster file, index, output raster file)
    #パラメータ入力画面の作成（入力画像名、指数、出力画像名）
    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.INPUT_RASTER,
            self.tr("Input Raster"), None, False))

        #指数の選択
        #インフラデータチャレンジの審査（2019/04）までに全ての指数を選択可能なコードに書き換えること
        # ["NDVI", "MSAVI", "VARI", "BAI"],
        self.addParameter(QgsProcessingParameterEnum(
            self.INPUT_MODE, 
            self.tr("MODE"), 
             ["NDVI"],
            False, None, False)
            )

        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT_RASTER,
            self.tr("Output Raster"),
            None, False))

    #パラメーターの変数への受け渡し
    #pass the parameters to variables
    def processAlgorithm(self, parameters, context, feedback):
        raster = self.parameterAsRasterLayer(parameters, self.INPUT_RASTER, context)
        mode_str = self.parameterAsString(parameters, self.INPUT_MODE,context)
        output_raster_path = self.parameterAsOutputLayer(parameters, self.OUTPUT_RASTER, context)

        #計算の実行
        #DO SOME CALCULATION
        QgsMessageLog.logMessage("Operation started")
        srcRas, width, height, nodata = self.get_band_array(raster.dataProvider().dataSourceUri())
        QgsMessageLog.logMessage(str(srcArray[0]))
        dstArray = self.calculate(mode_str, srcArray)
        self.write_array(output_raster_path, mode_str, srcRas, width, height, nodata, dstArray)
        results = {}
        results[self.OUTPUT_RASTER] = output_raster_path
        return results

    #ラスターを開いて4バンドを取得、配列の計算を実行
    #Open raster file, get the 4 bands and calculate the arrays
    def get_band_array(self, src):
        QgsMessageLog.logMessage("Get the bands and array")
        srcRas = gdal.Open(src, gdal.GA_ReadOnly)
        if srcRas.RasterCount != 4:
            QgsMessageLog.logMessage("Not enough bands")
            sys.exit()

        srcBand = []
        srcArray =[]
        nodata = []
        for i in [1,2,3,4]:
            srcBand.append(srcRas.GetRasterBand(i))
            nodata.append(srcBand[i-1].GetNoDataValue())
            srcArray.append(np.ma.masked_equal(srcBand[i-1].ReadAsArray(), nodata[i-1]).astype(np.float32))
            srcArray_str = str(srcArray)
            QgsMessageLog.logMessage(srcArray_str)
        src = None

        width = srcArray[i-1].shape[1]
        height = srcArray[i-1].shape[0]

        return srcRas, srcArray, width, height, nodata

    #指数の計算
    #calculate the index
    def calculate(self, mode_str, srcArray):
        QgsMessageLog.logMessage("Calculate the index")
        QgsMessageLog.logMessage(mode_str)

        #NDVI
        if mode_str == "0":
            NDVI_numerator = srcArray[3]-srcArray[2]
            NDVI_denominator = srcArray[3]+srcArray[2]
            dstArray = NDVI_numerator/NDVI_denominator

#        #VARI
#        elif mode_str == "1":
#            VARI_numerator = srcArray[1]-srcArray[2]
#            VARI_denominator = srcArray[1]+srcArray[2]-srcArray[0]
#            dstArray = VARI_numerator/VARI_denominator
#        #BAI
#        elif mode_str == "2":
#            B = np.apply_along_axis(lambda x: 0.1-x, 0, srcArray[2])
#            C = np.apply_along_axis(lambda x: 0.06-x, 0, srcArray[3])
#            dstArray = 1/(B**2 + C**2)

        dstArray_str = str(dstArray)
        QgsMessageLog.logMessage(dstArray_str)

        return dstArray

    #出力画像の作成
    #create the output raster file
    def write_array(self, output_raster_path, mode_str, srcRas, width, height, nodata, dstArray):
        QgsMessageLog.logMessage("Create the raster file and write the array into it")
        dstType = gdal.GDT_Float32
        geotransform = srcRas.GetGeoTransform()
        originX = geotransform[0]
        originY = geotransform[3]
        pixelWidth = geotransform[1]
        pixelHeight = geotransform[5]

        driver = gdal.GetDriverByName('GTiff')
        dstRas = driver.Create(output_raster_path, width, height, 1, dstType)
        dstRas.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
        dstBand = dstRas.GetRasterBand(1)
        dstBand.WriteArray(dstArray)
        if nodata[0]:
            dstBand.SetNoDataValue(nodata[0])

        dstBand.FlushCache()
        dstRas = None
        srcFirst = None