from keras.models import *
from keras.layers import Input, Activation, Conv2D, MaxPooling2D, Cropping2D
from keras.layers import BatchNormalization, ZeroPadding2D, Conv2DTranspose, concatenate
from keras.optimizers import *
from keras.callbacks import ModelCheckpoint, TensorBoard
from data_OnevsAll import *
import os

class myCNN(object):

    def __init__(self, img_rows, img_cols):
        self.img_rows = img_rows
        self.img_cols = img_cols
        self.batch_size = 10
        self.filter_size = 3
        self.channels = 4

    def load_data(self, mask):
        mydata = dataProcess(self.img_rows, self.img_cols)
        imgs_train, imgs_mask_train = mydata.load_train_data(mask)
        imgs_test, imgs_mask_test = mydata.load_test_data(mask)
        return imgs_train, imgs_mask_train, imgs_test, imgs_mask_test

    def BN_CONV_RELU(self, filters, kernel_size, inputs):
        return Activation(activation='relu')(
            Conv2D(filters, kernel_size, strides=(1, 1), padding='valid',
                   kernel_initializer='glorot_uniform', bias_initializer='zeros')(
                ZeroPadding2D(padding=(1, 1))(  # P=(F-1)/2=(3-1)/2=1
                    BatchNormalization()(inputs))))

    def BN_UPCONV_RELU(self, filters, kernel_size, inputs):
        return Activation(activation='relu')(
            Cropping2D(cropping=((1, 0), (0, 1)))(  # crop top row and right column
                Conv2DTranspose(filters, kernel_size, strides=(2, 2), padding='valid',
                                kernel_initializer='glorot_uniform', bias_initializer='zeros')(
                    BatchNormalization()(inputs))))

    def DOWN(self, channels, filter_size, inputs):
        return self.BN_CONV_RELU(channels, filter_size,
                                 self.BN_CONV_RELU(channels, filter_size, inputs))

    def UP(self, channels, filter_size, inputs, downinput):
        return self.BN_UPCONV_RELU(channels, filter_size,
                                   self.BN_CONV_RELU(channels, filter_size,
                                                     concatenate([inputs, downinput], axis=3)))

    def get_CNN(self):
        inputs = Input(shape=(self.img_rows, self.img_cols, 2))  # data_format=(batch, height, width, channels)

        down1 = self.DOWN(self.channels, self.filter_size, inputs)
        pool1 = MaxPooling2D(pool_size=(2, 2))(down1)
        print("down1 shape:", pool1.shape)
        down2 = self.DOWN(self.channels, self.filter_size, pool1)
        pool2 = MaxPooling2D(pool_size=(2, 2))(down2)
        print("down2 shape:", pool2.shape)
        down3 = self.DOWN(self.channels, self.filter_size, pool2)
        pool3 = MaxPooling2D(pool_size=(2, 2))(down3)
        print("down3 shape:", pool3.shape)

        #
        bcr6 = self.BN_CONV_RELU(self.channels, self.filter_size, pool3)
        bcr6 = self.BN_CONV_RELU(self.channels, self.filter_size, bcr6)
        bur6 = self.BN_UPCONV_RELU(self.channels, self.filter_size, bcr6)
        print("bur6 shape:", bur6._keras_shape)
        #

        up3 = self.UP(self.channels, self.filter_size, bur6, down3)
        print("up3 shape:", up3._keras_shape)
        up2 = self.UP(self.channels, self.filter_size, up3, down2)
        print("up2 shape:", up2._keras_shape)

        concat11 = concatenate([up2, down1], axis=3)
        bcr11 = self.BN_CONV_RELU(self.channels, self.filter_size, concat11)
        bcr11 = self.BN_CONV_RELU(self.channels, self.filter_size, bcr11)
        print("up1 shape:", bcr11.shape)

        convout11 = Conv2D(1, 1, strides=(1, 1), padding='valid', activation='sigmoid')(bcr11)
        print("convout shape:", convout11.shape)
        print()

        model = Model(inputs=inputs, outputs=convout11)
        model.summary()

        model.compile(optimizer=Adam(lr=1e-2), loss='binary_crossentropy',
                      metrics=['binary_accuracy'])

        return model

    def train(self, mask):
        print("loading data")
        imgs_train, imgs_mask_train, imgs_test, imgs_mask_test = self.load_data(mask)
        print("loading data done")
        model = self.get_CNN()
        print("got unet")

        tensorboard = TensorBoard(log_dir='{}/logs'.format(mask), histogram_freq=2, write_graph=True, write_grads = True, write_images=False)
        model_checkpoint = ModelCheckpoint('{}/CNNweights.hdf5'.format(mask), monitor='val_loss', verbose=1, save_best_only=True)
        print('Fitting model...')

        model.fit(imgs_train, imgs_mask_train, batch_size=self.batch_size, epochs=10, verbose=1, validation_split=0.2,
                  validation_data=(imgs_test, imgs_mask_test), shuffle=True, callbacks=[model_checkpoint, tensorboard])



if __name__ == '__main__':
    """
    If training One-vs-All Classifier for
        land : set mask=0
        sea  : set mask=1
        ships: set mask=2
    """
    mask = 0
    mycnn = myCNN(128, 128)
    mycnn.train(mask)